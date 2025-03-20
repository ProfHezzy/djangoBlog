from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm, LoginForm, BlogPostForm, CommentForm, ProfileUpdateForm
from .models import Profile, BlogPost, Comment, Follow, Like, Message, Notification, FriendRequest, Friendship
from django.db.models import Count
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Max
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import logging


User = get_user_model()
logger = logging.getLogger(__name__)
@login_required

def chat_list(request, receiver_username=None):
    """
    Displays the chat history of a logged-in user.
    """
    if not request.user.is_authenticated:
        logger.warning("User not authenticated!")
        return render(request, "chat_page.html", {"friends": []})

    # Get all messages where the user is either the sender or receiver
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-timestamp')

    friend_data = {}

    # Store unique chat users and their last message
    for message in messages:
        friend = message.sender if message.receiver == request.user else message.receiver
        if friend.username not in friend_data:
            friend_data[friend.username] = {
                "friend": friend,
                "recent_message": message.content,
                "last_chat_time": message.timestamp,
            }

    # Convert dict to sorted list (most recent chat first)
    friends = sorted(friend_data.values(), key=lambda x: x["last_chat_time"], reverse=True)

    logger.info(f"User: {request.user}, Friends: {friends}")

    # Fetch chat history with a selected user (if provided)
    receiver = None
    messages_history = None

    if receiver_username:
        receiver = get_object_or_404(User, username=receiver_username)
        messages_history = Message.objects.filter(
            Q(sender=request.user, receiver=receiver) | Q(sender=receiver, receiver=request.user)
        ).order_by('timestamp')

    context = {
        'friends': friends,
        'receiver': receiver,
        'messages_history': messages_history,
    }

    return render(request, "chat_page.html", context)


@login_required
def friends_list(request):
    friends = Friendship.objects.filter(user=request.user).values_list('friend', flat=True)
    sender = User.objects.filter(id__in=friends)
    return render(request, "friends_list.html", {"friends": sender})

def search_friends(request):
    query = request.GET.get('q', '').strip()
    users = []
    
    if query:
        users = User.objects.filter(username__icontains=query) | User.objects.filter(email__icontains=query)

    return render(request, 'search_friends.html', {'users': users, 'query': query})


@csrf_exempt
@login_required
def send_friend_request(request):
    if request.method == "POST":
        receiver_id = request.POST.get("receiver_id")
        receiver = User.objects.get(id=receiver_id)

        if FriendRequest.objects.filter(sender=request.user, receiver=receiver, status="pending").exists():
            return JsonResponse({"message": "Friend request already sent"}, status=400)

        FriendRequest.objects.create(sender=request.user, receiver=receiver)

        # Create a notification
        Notification.objects.create(user=receiver, message=f"{request.user.username} sent you a friend request.")

        return JsonResponse({"message": "Friend request sent successfully"}, status=200)
    
    
def search_friends(request):
    query = request.GET.get("q", "").strip()

    if query:
        users = User.objects.filter(username__icontains=query).values("username")
        return JsonResponse({"users": list(users)})

    return JsonResponse({"users": []})

def search_friends_page(request):
    return render(request, "search_friends.html")

# Handle AJAX request for searching users
def search_friends_ajax(request):
    query = request.GET.get("q", "").strip()

    if query:
        users = User.objects.filter(username__icontains=query).values("username")
        return JsonResponse({"users": list(users)})

    return JsonResponse({"users": []})

    
@login_required
def search_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(
        Q(username__icontains=query) | Q(email__icontains=query)
    ).exclude(username=request.user.username)  # Exclude the current user

    user_list = []
    for user in users:
        profile = Profile.objects.get(user=user)
        is_friend = FriendRequest.objects.filter(
            (Q(sender=request.user, receiver=user, status="accepted") |
            Q(sender=user, receiver=request.user, status="accepted"))
        ).exists()

        user_list.append({
            'username': user.username,
            'email': user.email,
            'profile_pic': profile.profile_picture.url if profile.profile_picture else None,
            'is_friend': is_friend,
        })

    return JsonResponse({'users': user_list})

def index(request):
    user_posts = BlogPost.objects.all().order_by('-created_at')

    if request.user.is_authenticated:
        followed_users = request.user.following.values_list('following', flat=True)

        # Create a dictionary to check if the logged-in user follows each post's author
        follow_status = {post.author.id: post.author.id in followed_users for post in user_posts}
    else:
        follow_status = {}

    return render(request, 'index.html', {"user_posts": user_posts, "follow_status": follow_status})



def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('user_login')  # Ensure login URL is correct
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    next_url = request.GET.get('next', None)  # Get the next URL if available
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                auth_login(request, user)
                print (user.is_authenticated)
                return redirect(next_url if next_url else 'profile', username=user.username)  # Redirect to next page or profile
            else:
                return render(request, 'login.html', {'form': form, 'error': 'Invalid Credentials'})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form, 'next': next_url})


@login_required
def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = BlogPost.objects.filter(author=profile_user)

    # Count total likes from the Like model
    total_likes = posts.aggregate(total_likes=Count('post_likes'))['total_likes'] or 0

    # Count total comments
    total_comments = posts.aggregate(total_comments=Count('comments'))['total_comments'] or 0

    # Count total followers
    total_followers = Follow.objects.filter(following=profile_user).count()

    # Count total following
    total_following = Follow.objects.filter(follower=profile_user).count()

    context = {
        'profile_user': profile_user,  # Pass the profile user
        'posts': posts,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'total_followers': total_followers,
        'total_following': total_following,
    }
    return render(request, 'profile.html', context)

def logout(request):
    auth_logout(request)
    return redirect('login')

def blog_detail(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    comments = post.comments.all()
    comment_form = CommentForm()

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.user = request.user
            new_comment.post = post
            new_comment.save()
            return redirect('blog_detail', post_id=post.id)

    return render(request, 'blog_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    })

@login_required
def add_post(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('profile', username=request.user.username)
    else:
        form = BlogPostForm()
    
    return render(request, 'add_post.html', {'form': form})

@login_required
def update_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    if post.author != request.user:
        return redirect('profile', username=request.user.username)

    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('profile', username=request.user.username)
    else:
        form = BlogPostForm(instance=post)

    return render(request, 'update_post.html', {'form': form, 'post': post})

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    # Ensure only the author can delete the post
    if post.author != request.user:
        return redirect('profile', username=request.user.username)

    post.delete()
    return redirect('profile', username=request.user.username)


@login_required
def like_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    user = request.user
    liked = False

    try:
        like = Like.objects.filter(user=user, post=post).first()

        if like:
            like.delete()
        else:
            Like.objects.create(user=user, post=post, created_at=now())
            liked = True

        if request.user != post.author:
            Notification.objects.create(
                user=post.author,
                sender=user,
                notification_type='like',
                post=post
            )

        return JsonResponse({'success': True, 'likes': post.post_likes.count(), 'liked': liked})

    except Exception as e:
        print(f"Error in like_post: {e}") # print the error to the console.
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


import datetime

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    if request.method == "POST":
        content = request.POST['content']
        comment = Comment.objects.create(user=request.user, post=post, content=content)

        Notification.objects.create(
            user=post.author,
            sender=request.user,
            notification_type='comment',
            post=post
        )
        return JsonResponse({
            'success': True,
            'comments': post.comments.count(),
            'user': request.user.username,
            'content': content,
            'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    else:
        return JsonResponse({'success': False})

def get_post_stats(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    return render(request, 'post_stats.html', {'post': post})

def get_post(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    return render(request, 'profile.html', {'post': post})

@login_required
def update_profile(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=request.user.username)
    else:
        form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'update_profile.html', {'form': form})

@login_required
def profile_update(request, username):
    user = get_object_or_404(User, username=username)
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile', username=user.username)

    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'profile_update.html', {'form': form})

@login_required
def follow_user(request, username):
    user_to_follow = get_object_or_404(User, username=username)
    if request.user != user_to_follow:
        Follow.objects.get_or_create(follower=request.user, following=user_to_follow)

        # Create a notification
        Notification.objects.create(
            user=user_to_follow,
            sender=request.user,
            notification_type='follow'
        )
    return redirect('profile', username=username)

@login_required
def unfollow_user(request, username):
    user_to_unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(follower=request.user, following=user_to_unfollow).delete()
    return redirect('profile', username=username)

def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    user_posts = BlogPost.objects.filter(author=user).order_by('-created_at')

    context = {
        'user': user,
        'cover_image': user.cover_pics.url if user.cover_pics else None
    }
    
    return render(request, 'profile.html', {'profile_user': user, 'user_posts': user_posts})

def navbar_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10] # Example of limiting to 10 notifications
    else:
        notifications = []
    return {'notifications': notifications}



@csrf_exempt
@login_required
def mark_notifications_as_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)


@login_required
def chat_page(request, username):
    chat_user = get_object_or_404(User, username=username)
    
    # Fetch chat messages
    messages = Message.objects.filter(
        Q(sender__in=[request.user, chat_user], receiver__in=[request.user, chat_user])
    ).order_by('timestamp').select_related('sender', 'receiver')

    # Mark messages as read
    Message.objects.filter(sender=chat_user, receiver=request.user, is_read=False).update(is_read=True)

    # Mark notifications as read
    Notification.objects.filter(
        user=request.user,
        sender=chat_user,
        notification_type='message',
        is_read=False
    ).update(is_read=True)

    # Check if they are friends
    are_friends = Friendship.objects.filter(
        Q(user=request.user, friend=chat_user) | Q(user=chat_user, friend=request.user)
    ).exists()

    # Check if a friend request is pending
    friend_request_sent = FriendRequest.objects.filter(sender=request.user, receiver=chat_user).exists()
    friend_request_received = FriendRequest.objects.filter(sender=chat_user, receiver=request.user).exists()

    return render(request, 'chat_page.html', {
        'chat_user': chat_user,
        'messages': messages,
        'are_friends': are_friends,
        'friend_request_sent': friend_request_sent,
        'friend_request_received': friend_request_received
    })




@csrf_exempt
@login_required
def send_message(request):
    if request.method == "POST":
        recipient_username = request.POST.get("recipient")
        content = request.POST.get("content")

        # Validate input
        if not recipient_username:
            return JsonResponse({"success": False, "error": "Recipient username is required"})
        if not content:
            return JsonResponse({"success": False, "error": "Message content cannot be empty"})

        # Fetch recipient
        recipient = get_object_or_404(User, username=recipient_username)

        # Ensure user is not sending a message to themselves
        if request.user == recipient:
            return JsonResponse({"success": False, "error": "You cannot send a message to yourself"})

        # Create message
        message = Message.objects.create(
            sender=request.user,
            receiver=recipient,
            content=content
        )

        # Create notification for the recipient
        Notification.objects.create(
            user=recipient,
            sender=request.user,
            notification_type='messages',  # Matches your NOTIFICATION_TYPES
            message=message,  # Link the message to the notification
        )

        # Return success response with message details
        return JsonResponse({
            "success": True,
            "message_id": message.id,
            "sender": message.sender.username,
            "receiver": message.receiver.username,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),  # ISO format for readability
        })

    return JsonResponse({"success": False, "error": "Invalid request method"})



@login_required
def get_messages(request, username):
    if request.method == "GET":
        recipient = get_object_or_404(User, username=username)

        offset = int(request.GET.get("offset", 0))  # Default offset is 0
        limit = int(request.GET.get("limit", 10))  # Default limit is 10 messages

        messages = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=recipient)) |
            (Q(sender=recipient) & Q(receiver=request.user))
        ).order_by("-timestamp")[offset:offset + limit]  # Order by latest first and apply pagination

        message_list = [
            {
                "id": message.id,
                "sender": message.sender.username,
                "receiver": message.receiver.username,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
            }
            for message in messages
        ]

        return JsonResponse({
            "success": True,
            "messages": message_list[::-1], 
            "has_more": messages.count() == limit  
        })

    return JsonResponse({"success": False, "error": "Invalid request method"})

@login_required
def get_new_messages(request, username):
    if request.method == "GET":
        # Fetch the recipient user
        recipient = get_object_or_404(User, username=username)

        # Get the timestamp of the last message the user has seen
        last_seen_timestamp = request.GET.get("last_seen_timestamp")
        if last_seen_timestamp:
            last_seen_timestamp = datetime.fromisoformat(last_seen_timestamp)
        else:
            last_seen_timestamp = None

        # Fetch new messages (messages sent after the last seen timestamp)
        messages = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=recipient)) |
            (Q(sender=recipient) & Q(receiver=request.user))
        )
        if last_seen_timestamp:
            messages = messages.filter(timestamp__gt=last_seen_timestamp)
        messages = messages.order_by("timestamp")

        # Serialize messages
        message_list = [
            {
                "id": message.id,
                "sender": message.sender.username,
                "receiver": message.receiver.username,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
            }
            for message in messages
        ]

        return JsonResponse({
            "success": True,
            "messages": message_list,
        })

    return JsonResponse({"success": False, "error": "Invalid request method"})


@login_required
def get_unread_count(request, username):
    chat_user = get_object_or_404(User, username=username)
    unread_count = Message.objects.filter(
        sender=chat_user,
        receiver=request.user,
        is_read=False
    ).count()
    print(f"Unread count for {username}: {unread_count}") #Added print statement.
    return JsonResponse({'unread_count': unread_count})

@login_required
def get_notification_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

def test_chat_link(request):
    test_user = User.objects.get(username='User1')  # Replace 'User1' with a known username
    return render(request, 'test_chat_link.html', {'chat_user': test_user})

def post_comments(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    comments = post.comments.all().order_by('-created_at')  # Order comments by creation time
    form = CommentForm() #create a new comment form.

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            return JsonResponse({'success': True, 'comments': post.comments.count(), 'user': request.user.username, 'content': comment.content, 'created_at': comment.created_at.strftime("%Y-%m-%d %H:%M:%S")})

    return render(request, 'post_comments.html', {'post': post, 'comments': comments, 'form': form})

@login_required
def mark_message_as_read(request, message_id):
    message = get_object_or_404(Message, id=message_id, receiver=request.user)
    message.is_read = True
    message.save()
    return JsonResponse({"success": True})

logger = logging.getLogger(__name__)
from django.http import JsonResponse, Http404

@login_required
@csrf_exempt
def delete_message(request, message_id):
    if request.method == 'POST':
        try:
            message = Message.objects.get(id=message_id)
            # Ensure only the sender or recipient can delete the message
            if request.user == message.sender or request.user == message.recipient:
                message.is_deleted = True  # Mark the message as deleted
                message.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Unauthorized'})
        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Message not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


'''@login_required
def send_friend_request(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier")  # Can be username or email
        try:
            # Find the user by username or email
            receiver = User.objects.get(username=identifier)
        except User.DoesNotExist:
            try:
                receiver = User.objects.get(email=identifier)
            except User.DoesNotExist:
                return JsonResponse({"success": False, "error": "User not found."})

        # Check if the user is trying to send a request to themselves
        if request.user == receiver:
            return JsonResponse({"success": False, "error": "You cannot send a friend request to yourself."})

        # Check if a friend request already exists
        if FriendRequest.objects.filter(sender=request.user, receiver=receiver).exists():
            return JsonResponse({"success": False, "error": "Friend request already sent."})

        # Create the friend request
        FriendRequest.objects.create(sender=request.user, receiver=receiver)
        return JsonResponse({"success": True, "message": "Friend request sent."})

    return JsonResponse({"success": False, "error": "Invalid request method."})'''

@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)
    friend_request.accepted = True
    friend_request.save()
    return JsonResponse({"success": True, "message": "Friend request accepted."})

@login_required
def reject_friend_request(request, request_id):
    friend_request = get_object_or_404(FriendRequest, id=request_id, receiver=request.user)
    friend_request.delete()
    return JsonResponse({"success": True, "message": "Friend request rejected."})

def get_message_updates(request, recipient_username):
    if request.method == 'GET':
        try:
            # Fetch messages where the current user is the recipient
            messages = Message.objects.filter(recipient__username=recipient_username, is_deleted=True)
            updates = [{
                'id': message.id,
                'content': 'Message Deleted',
                'is_deleted': True,
                'timestamp': message.timestamp.isoformat(),
            } for message in messages]
            return JsonResponse({'success': True, 'updates': updates})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




