from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, auth
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from school.models import Profile, Post, PostComment, Notification, LiveSession, LiveParticipant, CBTExam, CBTScore
from django.db.models import Q
import uuid, json

# ── existing views (unchanged) ────────────────────────────────────

def index(request):
    if request.user.is_authenticated:
        messages.info(request, f'Welcome back {request.user.username}')
        return redirect('home')
    if request.method == 'POST':
        user_check = request.POST.get('user_check')
        password   = request.POST.get('password')
        try:
            user_obj = User.objects.get(email=user_check)
            username = user_obj.username
        except User.DoesNotExist:
            username = user_check
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            messages.info(request, f'Welcome back {user.username}')
            request.session.set_expiry(None)
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.info(request, 'Check Login details')
            return redirect('/')
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST':
        username  = request.POST.get('username')
        email     = request.POST.get('email')
        fname     = request.POST.get('fname')
        lname     = request.POST.get('lname')
        password  = request.POST.get('pass1')
        password2 = request.POST.get('pass2')
        if len(username) < 5:
            messages.info(request, 'Username Characters Can not Less than 5 characters')
            return redirect('register')
        elif User.objects.filter(username=username).exists():
            messages.info(request, 'Username is taken Alredy')
            return redirect('register')
        elif User.objects.filter(email=email).exists():
            messages.info(request, 'Email is taken Alredy')
            return redirect('register')
        elif password != password2:
            messages.info(request, 'Password not Match')
            return redirect('register')
        else:
            user = User.objects.create_user(
                username=username, email=email,
                first_name=fname, last_name=lname, password=password
            )
            Profile.objects.create(user=user)
            CBTScore.objects.create(user=user)        # ← create score row on register
            messages.info(request, "You Successfully joined Login Now")
            return redirect('/')
    return render(request, 'register.html')


def home(request):
    return render(request, 'home.html')


def profile(request, username):
    user    = get_object_or_404(User, username=username)
    profile = Profile.objects.get(user=user)
    posts   = Post.objects.filter(author=user)
    total_view = sum(p.view for p in posts)

    # ── CBT data for the profile page ──
    cbt_score, _ = CBTScore.objects.get_or_create(user=user)
    recent_exams  = CBTExam.objects.filter(student=user)[:5]

    context = {
        'user':         user,
        'profile':      profile,
        'videos':       posts,
        'total_view':   total_view,
        'cbt_score':    cbt_score,
        'recent_exams': recent_exams,
    }
    return render(request, 'profile.html', context)


def update_profile(request, username):
    user    = request.user
    profile = request.user.profile
    if request.method == 'POST':
        fname   = request.POST.get('fname')
        lname   = request.POST.get('lname')
        bio     = request.POST.get('bio')
        phone   = request.POST.get('phone')
        address = request.POST.get('address')
        image   = request.FILES.get('image')
        if fname and lname:
            user.first_name = fname
            user.last_name  = lname
            user.save()
        if bio:     profile.bio     = bio
        if phone:   profile.phone   = phone
        if address: profile.address = address
        if image:   profile.picture = image
        profile.save()
        messages.info(request, 'Profile Updated')
        return redirect('profile', username=username)
    return render(request, 'updateprofile.html', {'profile': profile})


def follow(request, username):
    user    = get_object_or_404(User, username=username)
    profile = Profile.objects.get(user=user)
    if request.user not in profile.follow.all():
        profile.follow.add(request.user)
        profile.save()
        messages.info(request, 'Following')
    else:
        profile.follow.remove(request.user)
        profile.save()
        messages.info(request, 'Unfollow')
    return redirect(request.META.get('HTTP_REFERER'))


def post(request):
    if request.method == 'POST':
        title   = request.POST.get('title')
        about   = request.POST.get('about')
        video   = request.FILES.get('video')
        subject = request.POST.get('subject')
        if title and about and video and subject:
            Post.objects.create(author=request.user, title=title, about=about, video=video, subject=subject)
            messages.info(request, 'Video Upladed Successfully')
            return redirect(request.META.get('HTTP_REFERER'))
        else:
            messages.info(request, 'Please Fill all the Fields')
            return redirect(request.META.get('HTTP_REFERER'))
    videos = Post.objects.all().order_by('-created_at')
    return render(request, 'post.html', {'videos': videos})


def post_detail(request, post_id):
    video         = get_object_or_404(Post, post_id=post_id)
    comments      = PostComment.objects.filter(post=video).order_by('-created_at')
    total_comment = len(comments)
    video.view   += 1
    video.save()
    return render(request, 'postdetails.html', {'video': video, 'comments': comments, 'total_comment': total_comment})


def like(request, post_id):
    post = get_object_or_404(Post, post_id=post_id)
    if request.user not in post.like.all():
        post.like.add(request.user)
        post.save()
        if post.author != request.user:
            Notification.objects.create(
                user=post.author, post=post,
                message=f'{request.user.username} Liked your post {post.title}'
            )
    else:
        post.like.remove(request.user)
        post.save()
    return render(request, 'snippet/post_like.html', {'video': post, 'post_id': post_id})


def search(request):
    quary = request.GET.get('q')
    if quary:
        videos = Post.objects.filter(
            Q(title__icontains=quary) | Q(about__icontains=quary) | Q(subject__icontains=quary)
        ).order_by('-created_at')
        return render(request, 'search.html', {'videos': videos, 'quary': quary})
    return render(request, 'search.html')


def mathematics(request):
    videos = Post.objects.filter(subject__iexact='mathematics').order_by('-created_at')
    return render(request, 'mathematics.html', {'videos': videos})


def physics(request):
    videos = Post.objects.filter(subject__iexact='physics').order_by('-created_at')
    return render(request, 'physics.html', {'videos': videos})


def english(request):
    videos = Post.objects.filter(subject__iexact='english').order_by('-created_at')
    return render(request, 'english.html', {'videos': videos})


def chemistry(request):
    videos = Post.objects.filter(subject__iexact='chemistry').order_by('-created_at')
    return render(request, 'chemistry.html', {'videos': videos})


def notifications(request):
    return render(request, 'notification.html')


def open_notify(request, pk):
    notification          = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read  = True
    notification.save()
    if notification.post:
        return redirect('post_detail', post_id=notification.post.post_id)


def comment_like(request, comment_id):
    comment = get_object_or_404(PostComment, comment_id=comment_id)
    if request.user in comment.like.all():
        comment.like.remove(request.user)
    else:
        comment.like.add(request.user)
    return render(request, 'snippet/comment_like.html', {'comment': comment, 'comment_id': comment_id})


def post_comment(request, post_id):
    video = get_object_or_404(Post, post_id=post_id)
    if request.method == 'POST':
        comment = request.POST.get('comment', '').strip()
        if comment:
            comment = PostComment.objects.create(post=video, commentator=request.user, comment=comment)
            if video.author != request.user:
                Notification.objects.create(
                    user=video.author, post=video,
                    message=f'{request.user.username} Commented on your Post {video.title}'
                )
            return render(request, 'snippet/comments_list.html', {'video': video, 'comment': comment})


def user_logout(request):
    auth.logout(request)
    return redirect('/')


# ── Live Video Views ──────────────────────────────────────────────

@login_required
def live_room_list(request):
    active_sessions = LiveSession.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'live_room_list.html', {'sessions': active_sessions})


@login_required
def create_live_room(request):
    if request.method == 'POST':
        title     = request.POST.get('title')
        room_name = str(uuid.uuid4())[:8]
        if title:
            session = LiveSession.objects.create(
                room_name=room_name, title=title,
                created_by=request.user, is_active=True
            )
            messages.success(request, f'Live room "{title}" created successfully!')
            return redirect('live_room', room_name=room_name)
        else:
            messages.error(request, 'Please provide a title for your live session')
    return render(request, 'create_live_room.html')


@login_required
def live_room(request, room_name):
    session           = get_object_or_404(LiveSession, room_name=room_name, is_active=True)
    participant_count = LiveParticipant.objects.filter(session=session, is_connected=True).count()
    if participant_count >= session.max_participants:
        messages.error(request, 'This room is full. Please try again later.')
        return redirect('live_room_list')
    context = {
        'session':    session,
        'room_name':  room_name,
        'user':       request.user,
        'is_creator': session.created_by == request.user,
        'host_id':    session.created_by.id,   # ← used in template to route host stream to big stage
    }
    return render(request, 'live_room.html', context)


@login_required
def end_live_room(request, room_name):
    session           = get_object_or_404(LiveSession, room_name=room_name, created_by=request.user)
    session.is_active = False
    session.save()
    messages.success(request, 'Live session ended successfully')
    return redirect('live_room_list')


# ── CBT Exam Views ───────────────────────────────────────────────

@login_required
def cbt_subjects(request):
    """Render the CBT subject picker page."""
    return render(request, 'cbt_subjects.html')


@login_required
def cbt_exam(request):
    """Render the CBT exam page."""
    return render(request, 'cbt_exam.html')


@login_required
@require_POST
def cbt_submit(request):
    """
    AJAX endpoint.  Receives exam result as JSON, saves CBTExam + updates CBTScore.
    Expected body:
    {
        "subject":       "mathematics",
        "score":         15,
        "total":         20,
        "percentage":    75,
        "grade":         "distinction",
        "time_used_sec": 842
    }
    Returns:
    {
        "ok":     true,
        "points": 395,
        "best":   85
    }
    """
    try:
        data = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    subject       = data.get('subject', 'mathematics')
    score         = int(data.get('score', 0))
    total         = int(data.get('total', 20))
    percentage    = int(data.get('percentage', 0))
    grade         = data.get('grade', 'fail')
    time_used_sec = int(data.get('time_used_sec', 0))

    # Validate grade value
    valid_grades = [g[0] for g in CBTExam.GRADE_CHOICES]
    if grade not in valid_grades:
        grade = 'fail'

    # Save exam record
    CBTExam.objects.create(
        student       = request.user,
        subject       = subject,
        score         = score,
        total         = total,
        percentage    = percentage,
        grade         = grade,
        time_used_sec = time_used_sec,
    )

    # Update aggregated score
    cbt_score, _ = CBTScore.objects.get_or_create(user=request.user)
    cbt_score.recalculate()

    return JsonResponse({
        'ok':     True,
        'points': cbt_score.points,
        'best':   cbt_score.best_score,
    })
