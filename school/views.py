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


def _get_student_level(points):
    """
    Returns (level_name, level_number) for a given points total.
    Thresholds: Beginner → Bronze → Silver → Gold → Platinum → Champion
    """
    if points >= 2000:
        return ('Champion', 6)
    elif points >= 1000:
        return ('Platinum', 5)
    elif points >= 500:
        return ('Gold', 4)
    elif points >= 200:
        return ('Silver', 3)
    elif points >= 50:
        return ('Bronze', 2)
    else:
        return ('Beginner', 1)


def home(request):
    # ── Top-5 students by CBT points ──────────────────────────────
    top_scores = (
        CBTScore.objects
        .select_related('user', 'user__profile')
        .filter(points__gt=0)
        .order_by('-points')[:5]
    )

    top_students = []
    for position, score in enumerate(top_scores, start=1):
        level_name, level_num = _get_student_level(score.points)
        top_students.append({
            'position':   position,
            'user':       score.user,
            'profile':    score.user.profile,
            'points':     score.points,
            'attempts':   score.total_attempts,
            'best_score': score.best_score,
            'level_name': level_name,
            'level_num':  level_num,
        })

    return render(request, 'home.html', {'top_students': top_students})


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
        'host_id':    session.created_by.id,
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
def cbt_physics(request):
    """Render the Physics CBT exam page."""
    return render(request, 'cbt_physics.html')


@login_required
def cbt_english(request):
    """Render the English Language CBT exam page."""
    return render(request, 'cbt_english.html')


@login_required
def cbt_chemistry(request):
    """Render the Chemistry CBT exam page."""
    return render(request, 'cbt_chemistry.html')


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


# ── Student Scores Modal (AJAX / JSON) ──────────────────────────

@login_required
def student_scores_modal(request, username):
    """
    JSON endpoint called by the leaderboard modal JS in home.html.
    Returns all data needed to populate the modal (student info,
    per-subject breakdown, recent exams).

    Response shape:
    {
      "ok": true,
      "student": { username, full_name, picture_url, points, best_score,
                   total_attempts, total_correct, total_questions,
                   overall_rating, level_name, level_num,
                   grade, specialization, school_type },
      "subjects": [ { subject, attempts, best_score, best_total, best_pct,
                      best_grade, avg_pct, subject_rating, best_time_eff,
                      time_display, last_taken }, ... ],
      "recent_exams": [ { subject, score, total, percentage, grade,
                          rating, time_display, taken_at }, ... ]
    }
    """
    import math
    from django.db.models import Max, Avg, Sum, Count
    from django.utils.timezone import localtime

    user       = get_object_or_404(User, username=username)
    profile    = get_object_or_404(Profile, user=user)
    cbt_score, _ = CBTScore.objects.get_or_create(user=user)
    level_name, level_num = _get_student_level(cbt_score.points)

    # ── per-subject aggregates ────────────────────────────────────
    all_exams = CBTExam.objects.filter(student=user)

    subjects_data = []
    subject_names = all_exams.values_list('subject', flat=True).distinct()

    GRADE_ORDER = ['distinction', 'credit', 'pass', 'nearly', 'fail']
    GRADE_COLOR = {
        'distinction': '#16a34a',
        'credit':      '#2563eb',
        'pass':        '#d97706',
        'nearly':      '#ea580c',
        'fail':        '#dc2626',
    }

    for subj in subject_names:
        subj_qs = all_exams.filter(subject=subj)
        agg     = subj_qs.aggregate(
            best_pct=Max('percentage'),
            avg_pct=Avg('percentage'),
            attempts=Count('exam_id'),
            total_correct=Sum('score'),
            total_questions=Sum('total'),
        )

        best_exam = subj_qs.order_by('-percentage').first()
        last_exam = subj_qs.order_by('-taken_at').first()

        best_grade = best_exam.grade if best_exam else 'fail'
        best_pct   = round(agg['best_pct'] or 0)
        avg_pct    = round(agg['avg_pct'] or 0)

        # subject rating: weighted combo of best + avg
        subject_rating = min(100, round(best_pct * 0.6 + avg_pct * 0.4))

        # time efficiency: full marks in half the allowed time = 100 %
        # use best exam's time_used_sec; assume 60 s/question baseline
        if best_exam and best_exam.time_used_sec and best_exam.total:
            allowed_sec = best_exam.total * 60
            time_eff    = min(100, round((1 - best_exam.time_used_sec / allowed_sec) * 100 + 50))
        else:
            time_eff = 0

        # format best time
        if best_exam and best_exam.time_used_sec:
            m, s = divmod(best_exam.time_used_sec, 60)
            time_display = f'{m}m {s:02d}s'
        else:
            time_display = '—'

        last_taken = (
            localtime(last_exam.taken_at).strftime('%d %b %Y')
            if last_exam else '—'
        )

        subjects_data.append({
            'subject':        subj.capitalize(),
            'attempts':       agg['attempts'],
            'best_score':     best_exam.score if best_exam else 0,
            'best_total':     best_exam.total if best_exam else 0,
            'best_pct':       best_pct,
            'best_grade':     best_grade.capitalize(),
            'grade_color':    GRADE_COLOR.get(best_grade, '#606060'),
            'avg_pct':        avg_pct,
            'subject_rating': subject_rating,
            'best_time_eff':  time_eff,
            'time_display':   time_display,
            'last_taken':     last_taken,
        })

    # sort subjects by best_pct descending
    subjects_data.sort(key=lambda x: x['best_pct'], reverse=True)

    # ── recent exams (last 10) ────────────────────────────────────
    recent_exams_data = []
    for ex in all_exams.order_by('-taken_at')[:10]:
        if ex.time_used_sec:
            m, s = divmod(ex.time_used_sec, 60)
            t_display = f'{m}m {s:02d}s'
        else:
            t_display = '—'

        # per-exam rating: same weighted formula
        ex_rating = min(100, round(ex.percentage * 0.6 + ex.percentage * 0.4))

        recent_exams_data.append({
            'subject':      ex.subject.capitalize(),
            'score':        ex.score,
            'total':        ex.total,
            'percentage':   ex.percentage,
            'grade':        ex.grade.capitalize(),
            'rating':       ex_rating,
            'time_display': t_display,
            'taken_at':     localtime(ex.taken_at).strftime('%d %b %Y'),
        })

    # ── overall accuracy ─────────────────────────────────────────
    totals = all_exams.aggregate(
        total_correct=Sum('score'),
        total_questions=Sum('total'),
    )
    total_correct   = totals['total_correct']   or 0
    total_questions = totals['total_questions'] or 0

    # overall rating across all exams
    overall_rating = min(100, round(
        (cbt_score.best_score * 0.5 + (total_correct / total_questions * 100 if total_questions else 0) * 0.5)
    ))

    # ── profile fields (optional — Profile may not have these) ───
    def safe_get(obj, attr):
        return getattr(obj, attr, None) or ''

    return JsonResponse({
        'ok': True,
        'student': {
            'username':        user.username,
            'full_name':       user.get_full_name() or user.username,
            'picture_url':     profile.get_picture_url,
            'points':          cbt_score.points,
            'best_score':      cbt_score.best_score,
            'total_attempts':  cbt_score.total_attempts,
            'total_correct':   total_correct,
            'total_questions': total_questions,
            'overall_rating':  overall_rating,
            'level_name':      level_name,
            'level_num':       level_num,
            'grade':           safe_get(profile, 'grade'),
            'specialization':  safe_get(profile, 'specialization'),
            'school_type':     safe_get(profile, 'school_type'),
        },
        'subjects':     subjects_data,
        'recent_exams': recent_exams_data,
    })
