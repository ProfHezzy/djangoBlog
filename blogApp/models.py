from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

# User Profile Model
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default.jpg')
    cover_image = models.ImageField(upload_to='cover_pics/', blank=True, null=True)  # New Cover Image
    bio = models.TextField(max_length=500, blank=True)  # New Bio Field
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)

    is_moderator = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

# Blog Post Model
class BlogPost(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    video = models.FileField(upload_to='post_videos/', blank=True, null=True)

    def total_likes(self):
        return self.post_likes.count()  # FIXED: Uses Like model

    def total_comments(self):
        return self.comments.count()

    def __str__(self):
        return self.title

# Comment Model
class Comment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"

# Like Model (Track likes with timestamps)
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='post_likes')  # Related name fixed
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.user.username} likes {self.post.title}"

class Follow(models.Model):
    follower  = models.ForeignKey(User, related_name = 'following', on_delete = models.CASCADE)
    following = models.ForeignKey(User, related_name = 'follower', on_delete = models.CASCADE)
    created_at = models.DateTimeField(auto_now_add = True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower} follows {self.following}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"
    
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('messages', 'Messages')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")  # Recipient
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_sender")  # Who triggered it
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, null=True, blank=True)  # Optional (for likes/comments)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True) # Add this line
    is_read = models.BooleanField(default=False)  # Mark as read/unread
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} {self.get_notification_type_display()} {self.user}"
    

class FriendRequest(models.Model):
    sender = models.ForeignKey(User, related_name="sent_requests", on_delete=models.CASCADE, default=1)  # Temporary default
    receiver = models.ForeignKey(User, related_name="received_requests", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")],
        default="pending"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

class Friendship(models.Model):
    user = models.ForeignKey(User, related_name="friendships", on_delete=models.CASCADE)
    friend = models.ForeignKey(User, related_name="friends", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "friend")

    def __str__(self):
        return f"{self.user.username} - {self.friend.username}"