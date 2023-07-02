# ccExtractorDjangoProject

Problen Statement : 
You need to create a website on which video(s) can be uploaded, processed in some manner
(in the background) and then searched using the subtitles in that video as keywords.
For instance, if I were to upload a 2 minute clip of a music video, your application should parse
it, apply subtitles to it and ensure that searching for a particular word or phrase returns the time
segment within which the video has those phrases being mentioned.


1] The backend implementation is based on the Django framework.

2] We utilized the ccextractor binary to extract subtitles from the video.

3] Subsequently, the processed videos will be uploaded to S3, and the keywords will be queried from the DynamoDB, specifically from the subtitles.

