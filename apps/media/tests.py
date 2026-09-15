import io
from PIL import Image
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.media.validators import UploadValidator
from apps.media.processors import ImageProcessor
from apps.media.thumbnails import ThumbnailGenerator

def create_test_image(width=800, height=600, format='JPEG', filename='test.jpg'):
    file_obj = io.BytesIO()
    mode = 'RGB' if format == 'JPEG' else 'RGBA'
    image = Image.new(mode, size=(width, height), color=(255, 0, 0))
    if format == 'JPEG':
        image.save(file_obj, format=format, quality=90)
    else:
        image.save(file_obj, format=format)
    file_obj.seek(0)
    
    content_type = 'image/jpeg'
    if format == 'PNG':
        content_type = 'image/png'
    elif format == 'WEBP':
        content_type = 'image/webp'
    
    return SimpleUploadedFile(filename, file_obj.read(), content_type=content_type)


class TestUploadValidator(TestCase):
    
    def test_accepts_valid_jpeg(self):
        file = create_test_image(format='JPEG', filename='test.jpg')
        validator = UploadValidator(upload_type='cover')
        validator.validate(file)
        
    def test_accepts_valid_png(self):
        file = create_test_image(format='PNG', filename='test.png')
        validator = UploadValidator(upload_type='cover')
        validator.validate(file)
        
    def test_accepts_valid_webp(self):
        file = create_test_image(format='WEBP', filename='test.webp')
        validator = UploadValidator(upload_type='cover')
        validator.validate(file)
        
    def test_rejects_exe_extension(self):
        file = SimpleUploadedFile('malware.exe', b'MZ144', content_type='application/x-msdownload')
        validator = UploadValidator(upload_type='cover')
        with self.assertRaises(ValidationError):
            validator.validate(file)
            
    def test_rejects_php_extension(self):
        file = SimpleUploadedFile('shell.php', b'<?php phpinfo(); ?>', content_type='application/x-php')
        validator = UploadValidator(upload_type='cover')
        with self.assertRaises(ValidationError):
            validator.validate(file)
            
    def test_rejects_oversized_profile(self):
        file_obj = io.BytesIO(b'0' * (3 * 1024 * 1024))
        file = SimpleUploadedFile('test.jpg', file_obj.read(), content_type='image/jpeg')
        validator = UploadValidator(upload_type='profile')
        with self.assertRaises(ValidationError):
            validator.validate(file)
            
    def test_rejects_oversized_cover(self):
        file_obj = io.BytesIO(b'0' * (6 * 1024 * 1024))
        file = SimpleUploadedFile('test.jpg', file_obj.read(), content_type='image/jpeg')
        validator = UploadValidator(upload_type='cover')
        with self.assertRaises(ValidationError):
            validator.validate(file)
            
    def test_accepts_within_size_limit(self):
        file = create_test_image(format='JPEG', filename='test.jpg')
        validator = UploadValidator(upload_type='profile')
        validator.validate(file)
        
    def test_rejects_non_image_content_type(self):
        file = SimpleUploadedFile('test.pdf', b'%PDF-1.4', content_type='application/pdf')
        validator = UploadValidator(upload_type='cover')
        with self.assertRaises(ValidationError):
            validator.validate(file)
            
    def test_rejects_spoofed_file(self):
        file = SimpleUploadedFile('test.jpg', b'just some text', content_type='image/jpeg')
        validator = UploadValidator(upload_type='cover')
        with self.assertRaises(ValidationError):
            validator.validate(file)

    def test_validates_file_even_after_stream_has_been_read(self):
        file = create_test_image(format='JPEG', filename='test.jpg')
        file.read(4)
        validator = UploadValidator(upload_type='cover')
        validator.validate(file)


class TestImageProcessor(TestCase):

    def test_converts_to_webp(self):
        file = create_test_image(format='JPEG', filename='test.jpg')
        processor = ImageProcessor()
        result = processor.process(file)
        self.assertEqual(result['format'], 'webp')
        img = Image.open(result['buffer'])
        self.assertEqual(img.format, 'WEBP')

    def test_strips_exif(self):
        file = create_test_image(format='JPEG', filename='test.jpg')
        processor = ImageProcessor()
        result = processor.process(file)
        img = Image.open(result['buffer'])
        self.assertIsNone(img.getexif().get(274))

    def test_resizes_large_image(self):
        file = create_test_image(width=4000, height=3000, format='JPEG', filename='large.jpg')
        processor = ImageProcessor(max_dimension=1600)
        result = processor.process(file)
        img = Image.open(result['buffer'])
        self.assertLessEqual(max(img.width, img.height), 1600)

    def test_handles_rgba(self):
        file = create_test_image(format='PNG', filename='test.png')
        processor = ImageProcessor()
        result = processor.process(file)
        img = Image.open(result['buffer'])
        self.assertEqual(img.mode, 'RGB')

    def test_processes_file_even_after_stream_has_been_read(self):
        file = create_test_image(format='JPEG', filename='test.jpg')
        file.read(4)
        processor = ImageProcessor()
        result = processor.process(file)
        self.assertEqual(result['format'], 'webp')

    def test_compression(self):
        file = create_test_image(width=800, height=600, format='JPEG', filename='test.jpg')
        processor = ImageProcessor()
        result = processor.process(file)
        self.assertTrue(result['size'] > 0)


class TestThumbnailGenerator(TestCase):

    def test_generates_all_sizes(self):
        file = create_test_image(width=1200, height=800, format='JPEG', filename='test.jpg')
        generator = ThumbnailGenerator()
        thumbnails = generator.generate(file)
        self.assertIn('thumbnail', thumbnails)
        self.assertIn('medium', thumbnails)
        self.assertIn('large', thumbnails)

    def test_thumbnail_dimensions(self):
        file = create_test_image(width=1200, height=800, format='JPEG', filename='test.jpg')
        generator = ThumbnailGenerator()
        thumbnails = generator.generate(file)
        thumb_data = thumbnails['thumbnail']
        img = Image.open(thumb_data['buffer'])
        self.assertLessEqual(img.width, 300)

    def test_skips_upscaling(self):
        file = create_test_image(width=200, height=200, format='JPEG', filename='test.jpg')
        generator = ThumbnailGenerator()
        thumbnails = generator.generate(file)
        large_data = thumbnails['large']
        img = Image.open(large_data['buffer'])
        self.assertLessEqual(img.width, 200)
