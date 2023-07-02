from django.views import View
from django.shortcuts import render, redirect
from video_app.forms import VideoUploadForm
from django.http import HttpResponse
import subprocess
import os
import boto3
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from botocore.exceptions import NoCredentialsError
from django.http import JsonResponse
import tempfile
import logging

# Create a logger instance
logger = logging.getLogger(__name__)

class VideoUploadView(View):
    def get(self, request):
        form = VideoUploadForm()
        return render(request, 'upload.html', {'form': form})

    @csrf_exempt
    def post(self, request):
    
        if request.method == 'POST' and request.FILES.get('video'):
            video = request.FILES['video']
            video_file_path = os.path.join(settings.MEDIA_ROOT, 'temp', video.name)
            with open(video_file_path, 'wb') as file:
                for chunk in video.chunks():
                    file.write(chunk)
            bucket_name = "assignment-internship"
            ccextractor_path = 'C:\\Users\\Rahul\\Desktop\\Assignment-django\\video_processing\\media\\ccextractor\\ccextractorwin.exe'
            output_file_path = 'subtitles.srt'
            command = [ccextractor_path, video_file_path, '-o', output_file_path]

            try:
                subprocess.run(command, check=True)

                # Upload the video to S3
                with open(video_file_path, 'rb') as file:
                    if upload_video_to_s3(file, bucket_name):
                        # Close the file before removing it
                        file.close()

                        # Upload the subtitle file to DynamoDB
                        with open(output_file_path, 'r') as subtitle_file:
                            subtitle_content = subtitle_file.read()
                            upload_subtitle_to_dynamodb(video.name, subtitle_content)

                        # Serve the subtitle file as a response
                        with open(output_file_path, 'r') as subtitle_file:
                            response = HttpResponse(subtitle_file, content_type='application/octet-stream')
                            # response['Content-Disposition'] = 'attachment; filename="subtitles.srt"'
                            return response
                            # return redirect('search')
                    else:
                        return JsonResponse({'message': 'Failed to upload video'}, status=500)

            except subprocess.CalledProcessError:
                return HttpResponse("Error: Failed to extract subtitles.")

        else:
            return JsonResponse({'message': 'Invalid request'}, status=400)
        

def upload_subtitle_to_dynamodb(video_name, subtitle_content):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'VideoSubtitles'
    table = dynamodb.Table(table_name)

    table.put_item(
        Item={
            'video_id': video_name,
            'subtitle_content': subtitle_content
        }
    )

def upload_video_to_s3(file, bucket_name, object_name=None):
 
    object_name = file.name

    # Create a new S3 client
    s3_client = boto3.client('s3')

    try:
        # Upload the file to S3 bucket
        s3_client.upload_fileobj(file, bucket_name, object_name)
        return True
    except NoCredentialsError:
        return False

def perform_create(self, serializer):
    video_file = self.request.FILES['video_file']
    subtitle_file = self.request.FILES['subtitle_file']
    
    # Save video file to S3
    s3 = boto3.client('s3')
    video_file_key = f'videos/{video_file.name}'
    s3.upload_fileobj(video_file, settings.AWS_STORAGE_BUCKET_NAME, video_file_key)
    
    video = serializer.save(subtitle_file_key=subtitle_file.name)
    
    # Save subtitle file content to DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table_name = 'VideoSubtitles'
    table = dynamodb.Table(table_name)
    
    with subtitle_file.open('r') as file:
        subtitle_content = file.read()
        
    table.put_item(
        Item={
            'video_id': video.id,
            'subtitle_content': subtitle_content
        }
    )

class VideoSearchView(View):
    def get(self, request):
        form = VideoUploadForm()
        return render(request, 'search_keyword.html', {'form': form})
    
    def post(self, request):
        if 'keywords' in request.POST:
            keywords = request.POST['keywords']

            # Query DynamoDB based on search keywords
            results = search_video_segments_in_dynamodb(keywords)
            

             # Pass the results to the template for rendering
            return render(request, 'search_results.html', {'results': results})
        else:
            return JsonResponse({'message': 'Invalid request'}, status=400)

def search_video_segments_in_dynamodb(keywords):
    dynamodb = boto3.resource('dynamodb')
    table_name = 'VideoSubtitles'
    table = dynamodb.Table(table_name)
    
    
    temp_folder = os.path.join(settings.MEDIA_ROOT, 'temp')
    video_files = os.listdir(temp_folder)
    default_video = video_files[0]    
    item_key = default_video

    os.remove(os.path.join(settings.MEDIA_ROOT, 'temp', default_video))
    
    # Retrieve the item from DynamoDB
    response = table.get_item(
        Key={
            'video_id': item_key
        }   
    )

    item = response.get('Item')

    if item is not None and 'subtitle_content' in item:
        srt_content = item['subtitle_content']

        if isinstance(srt_content, str):
            subtitles = srt_content.strip().split('\n\n')
            results = []

            for subtitle in subtitles:
                lines = subtitle.split('\n')
                time_segment = lines[1].split(' --> ')
                subtitle_text = ' '.join(lines[2:])

                if keywords in subtitle_text:
                    results.append({
                        'start_time': time_segment[0],
                        'end_time': time_segment[1],
                        'text': subtitle_text
                    })

            return results