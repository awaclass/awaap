from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import User
from django.conf import settings
from django.templatetags.static import static
import uuid


# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    if settings.USE_CLOUDINARY:
        picture = CloudinaryField('picture', folder='profile_image', default='logo_iowyea')
    else:
        picture = models.ImageField(upload_to='profile_image/', default='male.png')

    follow = models.ManyToManyField(User, related_name='profile_like', blank=True)
    gender = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.CharField(max_length=300, blank=True)
    address = models.CharField(max_length=200, blank=True)
    about = models.CharField(max_length=300, blank=True)
    location = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user.first_name:
            self.user.first_name = self.user.first_name.capitalize()
        if self.user.last_name:
            self.user.last_name = self.user.last_name.capitalize()
        if self.bio:
            self.bio = self.bio.capitalize()
        if self.about:
            self.about = self.about.capitalize()
        if self.address:
            self.address = self.address.title()
        if self.location:
            self.location = self.location.title()
        self.user.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

    @property
    def get_picture_url(self):
        """
        Always returns a full usable picture URL in both environments.

        Production (USE_CLOUDINARY=True):
          Builds https://res.cloudinary.com/... from the stored public_id.
          Falls back to the default avatar if picture is blank.

        Debug (USE_CLOUDINARY=False):
          Returns the /media/... path via Django storage.
          Falls back to /static/images/male.png if file is missing.
        """
        try:
            if getattr(settings, 'USE_CLOUDINARY', False):
                import cloudinary
                pic = self.picture
                # CloudinaryField exposes .public_id; plain string fallback
                public_id = None
                if hasattr(pic, 'public_id') and pic.public_id:
                    public_id = str(pic.public_id).strip()
                elif pic and str(pic).strip() not in ('', 'None'):
                    public_id = str(pic).strip()

                if public_id:
                    return cloudinary.CloudinaryImage(public_id).build_url(secure=True)

                # No picture stored — return the default avatar
                return cloudinary.CloudinaryImage('logo_iowyea').build_url(secure=True)

            else:
                # Debug: standard ImageField
                pic = self.picture
                if pic and hasattr(pic, 'url'):
                    try:
                        url = pic.url
                        if url:
                            return url
                    except Exception:
                        pass
                # Fallback to a static default image
                return static('images/male.png')

        except Exception:
            pass

        return 'https://placehold.co/40x40/dbdbdb/8e8e8e?text=U'


class Post(models.Model):
    post_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_author')
    title = models.CharField(max_length=300)
    about = models.CharField(max_length=400)

    if settings.USE_CLOUDINARY:
        video = CloudinaryField('video', resource_type='video', folder='post_videos', blank=True)
    else:
        video = models.FileField(upload_to='post_videos/')

    subject = models.CharField(max_length=100, blank=True)
    like = models.ManyToManyField(User, related_name='post_like', blank=True)
    view = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_video_url(self):
        """
        Always returns a usable video URL in both environments.

        Production (USE_CLOUDINARY=True):
          Builds https://res.cloudinary.com/... from the stored public_id.

        Debug (USE_CLOUDINARY=False):
          Returns the /media/... path via Django storage.
        """
        try:
            if getattr(settings, 'USE_CLOUDINARY', False):
                import cloudinary
                vid = self.video
                public_id = None
                if hasattr(vid, 'public_id') and vid.public_id:
                    public_id = str(vid.public_id).strip()
                elif vid and str(vid).strip() not in ('', 'None'):
                    public_id = str(vid).strip()

                if public_id:
                    return cloudinary.CloudinaryVideo(public_id).build_url(secure=True)

            else:
                if self.video and hasattr(self.video, 'url'):
                    try:
                        url = self.video.url
                        if url:
                            return url
                    except Exception:
                        pass

        except Exception:
            pass

        return None


class PostComment(models.Model):
    comment_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    commentator = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='posts')
    comment = models.TextField()
    like = models.ManyToManyField(User, related_name='comment_likes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# Live Video Models
class LiveSession(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    room_name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=300)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=50)
    
    def __str__(self):
        return self.title


class LiveParticipant(models.Model):
    participant_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_participations')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_connected = models.BooleanField(default=True)
    is_video_on = models.BooleanField(default=True)
    is_audio_on = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['session', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.session.title}"
        
# ─────────────────────────────────────────────────────────────────
# ADD THESE TWO MODELS AT THE BOTTOM OF YOUR EXISTING models.py
# ─────────────────────────────────────────────────────────────────

class CBTExam(models.Model):
    """Stores a CBT exam attempt result for a user."""
    SUBJECT_CHOICES = [
        ('mathematics', 'Mathematics'),
        ('physics',     'Physics'),
        ('english',     'English'),
        ('chemistry',   'Chemistry'),
    ]
    GRADE_CHOICES = [
        ('distinction', 'Distinction'),
        ('credit',      'Credit'),
        ('pass',        'Pass'),
        ('nearly',      'Nearly'),
        ('fail',        'Fail'),
    ]

    exam_id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cbt_exams')
    subject       = models.CharField(max_length=30, choices=SUBJECT_CHOICES, default='mathematics')
    score         = models.PositiveIntegerField(default=0)          # raw correct answers
    total         = models.PositiveIntegerField(default=20)         # total questions
    percentage    = models.PositiveIntegerField(default=0)          # 0-100
    grade         = models.CharField(max_length=20, choices=GRADE_CHOICES, default='fail')
    time_used_sec = models.PositiveIntegerField(default=0)          # seconds spent
    taken_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-taken_at']

    def __str__(self):
        return f"{self.student.username} – {self.subject} – {self.score}/{self.total} ({self.percentage}%)"

    @property
    def time_display(self):
        m = self.time_used_sec // 60
        s = self.time_used_sec % 60
        return f"{m:02d}:{s:02d}"


class CBTScore(models.Model):
    """
    Aggregated lifetime CBT stats per user (one row per user).
    Updated every time a new CBTExam is saved.
    """
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cbt_score')
    total_attempts  = models.PositiveIntegerField(default=0)
    total_correct   = models.PositiveIntegerField(default=0)   # sum of all correct answers
    total_questions = models.PositiveIntegerField(default=0)   # sum of all questions attempted
    best_score      = models.PositiveIntegerField(default=0)   # highest % ever
    points          = models.PositiveIntegerField(default=0)   # gamified points

    def __str__(self):
        return f"{self.user.username} CBT Points: {self.points}"

    def recalculate(self):
        """Recompute all fields from the user's CBTExam history."""
        exams = CBTExam.objects.filter(student=self.user)
        self.total_attempts  = exams.count()
        self.total_correct   = sum(e.score for e in exams)
        self.total_questions = sum(e.total for e in exams)
        best = exams.order_by('-percentage').first()
        self.best_score      = best.percentage if best else 0
        # Points formula: 5 pts per correct answer + 20 bonus for Distinction
        self.points = sum(
            e.score * 5 + (20 if e.grade == 'distinction' else 0)
            for e in exams
        )
        self.save()
