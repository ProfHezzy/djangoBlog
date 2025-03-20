from django.contrib import admin
from .models import Profile, BlogPost, Follow, Notification

# Register your models here.
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_moderator', 'profile_picture', 'bio')

class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'updated_at')
    search_fields = ('title', 'author_username')
    list_filter = ('author', 'created_at')

admin.site.register(Profile, ProfileAdmin)
admin.site.register(BlogPost, BlogPostAdmin)
admin.site.register(Follow)
admin.site.register(Notification)

