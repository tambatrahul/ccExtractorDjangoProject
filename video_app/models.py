from django.db import models

class Video(models.Model):
    title = models.CharField(max_length=100)
    video_file = models.FileField(upload_to='videos/')
    subtitle_file = models.FileField(upload_to='subtitles/')

class Subtitle(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    text = models.TextField()