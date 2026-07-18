from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth import authenticate
from django.contrib.auth import login as login_user

from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework import status

from .forms import EditProfileForm, CreateProjectForm
from .serializers import EducationSerializer

from info.models import Information, Message, Project, Education


class CsrfExemptSessionAuthentication(authentication.SessionAuthentication):
    def enforce_csrf(self, request):
        return


# we use this class to login and check the user if she/he logged in.
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)

        if not username or not password:
            return render(request, "login.html", {'message': 'Please enter both username and password'})

        user = authenticate(
            username=username,
            password=password
        )
        if user:
            login_user(request, user)
            return redirect('dashboard:dashboard')
        return render(request, "login.html", {'message': 'Invalid Username or Password'})

    def get(self, request):
        return render(request, "login.html", {})


@login_required()
def dashboard(request):
    template_name = 'dashboard.html'
    profile = Information.objects.first()
    return render(request, template_name, {'profile': profile, 'dashboard': True})


@login_required()
def profile(request):
    template_name = 'profile.html'
    context = {}
    profile_obj = Information.objects.first()
    context.update({'profile_active': True, 'profile': profile_obj})
    return render(request, template_name, context)


@login_required()
def profile_edit(request):
    if request.method == 'POST':
        instance = Information.objects.first()

        avatar = request.FILES.get('avatar', False)
        if avatar:
            account = Information.objects.first()
            account.avatar = avatar
            account.save()
            return redirect('dashboard:profile')
        else:
            form = EditProfileForm(instance=instance, data=request.POST)
            if form.is_valid():
                form.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'status': 'bad request'})


@login_required()
def messages(request):
    template_name = 'messages.html'
    context = {}
    profile = Information.objects.first()
    message_list = Message.objects.all().order_by('-send_time')

    page = request.GET.get('page', 1)

    paginator = Paginator(message_list, 6)

    try:
        message_list = paginator.page(page)
    except PageNotAnInteger:
        message_list = paginator.page(1)
    except EmptyPage:
        message_list = paginator.page(paginator.num_pages)

    context.update({'messages_active': True, 'messages': message_list, 'profile': profile})
    return render(request, template_name, context)


@login_required()
def messages_api(request):
    if request.method == 'POST':
        option_type = request.POST.get('option_type')
        message_id = request.POST.get('message_id')
        if option_type == "delete":
            message = Message.objects.get(id=int(message_id))
            message.delete()
            return JsonResponse({'status': 'success'})
        elif option_type == "view":
            message = Message.objects.get(id=int(message_id))
            if not message.is_read:
                message.is_read = True
                message.save()
            return JsonResponse({'status': 'success'})
        elif option_type == "search":
            search_text = request.POST.get('search_text')

            lookups = Q(name__icontains=search_text) | Q(
                email__icontains=search_text) | Q(message__icontains=search_text)

            message_list = Message.objects.filter(lookups).values()
            message_list = list(message_list)

            return JsonResponse({'status': 'success', 'messages': message_list})
    return JsonResponse({'status': 'bad request'})


@login_required()
def projects(request):
    template_name = 'dashboard_projects.html'
    context = {}
    profile = Information.objects.first()
    project_list = Project.objects.all().order_by('-id')
    context.update({'projects_active': True, 'projects': project_list, 'profile': profile})
    return render(request, template_name, context)


@login_required()
def projects_api(request):
    if request.method == 'POST':
        request_type = request.POST.get('type')

        if request_type == 'create':
            form = CreateProjectForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return JsonResponse({'status': 'Create Project Successfully', 'code': 200})
            else:
                return JsonResponse({'status': 'Create Project Failed', 'code': 400, 'errors': form.errors})

        elif request_type == 'update':
            project_id = int(request.POST.get('id'))
            if request.POST.get('first', False):
                project = Project.objects.filter(id=project_id).values()
                return JsonResponse({'project': list(project)[0], 'code': 200})
            else:
                project = Project.objects.get(id=project_id)
                form = CreateProjectForm(request.POST, request.FILES, instance=project)
                if form.is_valid():
                    form.save()
                    return JsonResponse({'status': 'Update Project Successfully', 'code': 200})
                else:
                    return JsonResponse({'status': 'Update Project Failed', 'code': 400, 'errors': form.errors})

        elif request_type == 'delete':
            project_id = int(request.POST.get('id'))
            Project.objects.filter(id=project_id).delete()
            return JsonResponse({'status': 'Remove Project Successfully', 'code': 200})

    return JsonResponse({'status': 'Bad Request'})


class EducationView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        education = Education.objects.all()
        return render(request, 'dashboard_education.html', {'education': education})

    def post(self, request):
        serializer = EducationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
