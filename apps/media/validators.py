import logging
import io
import os
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Default configuration (can be overridden in settings)
DEFAULT_ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'avif'}
DEFAULT_BLOCKED_EXTENSIONS = {'exe', 'php', 'js', 'html', 'htm', 'zip', 'rar', 'apk', 'svg', 'bat', 'cmd', 'sh', 'py', 'rb', 'pl', 'cgi', 'asp', 'aspx', 'jsp'}
DEFAULT_MAX_SIZES = {
    'profile': 2 * 1024 * 1024,     # 2MB
    'cover': 5 * 1024 * 1024,       # 5MB  
    'gallery': 10 * 1024 * 1024,    # 10MB
    'editor': 5 * 1024 * 1024,      # 5MB for inline editor images
}

# Mapping of Pillow format names to expected extensions
FORMAT_TO_EXTENSIONS = {
    'JPEG': {'jpg', 'jpeg'},
    'PNG': {'png'},
    'WEBP': {'webp'},
    'AVIF': {'avif'},
}

class UploadValidator:
    """Validator for file uploads to check extension, content type, size, and magic bytes."""

    def __init__(self, upload_type='cover'):
        self.upload_type = upload_type
        self.allowed_extensions = self._get_allowed_extensions()
        self.blocked_extensions = self._get_blocked_extensions()
        self.max_size = self._get_max_size()

    def _get_allowed_extensions(self):
        return getattr(settings, 'MEDIA_ALLOWED_EXTENSIONS', DEFAULT_ALLOWED_EXTENSIONS)

    def _get_blocked_extensions(self):
        return getattr(settings, 'MEDIA_BLOCKED_EXTENSIONS', DEFAULT_BLOCKED_EXTENSIONS)

    def _get_max_size(self):
        sizes = getattr(settings, 'MEDIA_UPLOAD_MAX_SIZE', DEFAULT_MAX_SIZES)
        return sizes.get(self.upload_type, 5 * 1024 * 1024)

    def validate_extension(self, filename):
        ext = os.path.splitext(filename)[1].lower().strip('.')
        if not ext:
            logger.warning(f"File upload rejected: Missing extension in '{filename}'")
            raise ValidationError("File has no extension.")
        if ext in self.blocked_extensions:
            logger.warning(f"File upload rejected: Blocked extension '{ext}' in '{filename}'")
            raise ValidationError(f"File extension '{ext}' is not allowed.")
        if ext not in self.allowed_extensions:
            logger.warning(f"File upload rejected: Unsupported extension '{ext}' in '{filename}'")
            raise ValidationError(f"File extension '{ext}' is not supported.")
        return ext

    def validate_content_type(self, content_type):
        if not content_type or not content_type.startswith('image/'):
            logger.warning(f"File upload rejected: Invalid content type '{content_type}'")
            raise ValidationError("Invalid content type. Expected an image.")
        return content_type

    def validate_file_size(self, file_size):
        if file_size > self.max_size:
            logger.warning(f"File upload rejected: Size {file_size} exceeds max size {self.max_size} for type '{self.upload_type}'")
            raise ValidationError(f"File size exceeds the limit of {self.max_size / (1024 * 1024):.1f}MB.")
        return file_size

    def validate_magic_bytes(self, file_obj, ext):
        try:
            # Always rewind to the start so validation works even when a prior read moved the pointer.
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            # Check image magic bytes using Pillow
            with Image.open(file_obj) as img:
                img.verify()  # verify checks the integrity without fully loading
                file_format = img.format

                # Verify that format matches extension
                expected_exts = FORMAT_TO_EXTENSIONS.get(file_format, set())
                if expected_exts and ext not in expected_exts:
                    logger.warning(f"File upload rejected: Format {file_format} does not match extension '{ext}'")
                    raise ValidationError("File extension does not match its contents.")
        except UnidentifiedImageError:
            logger.warning("File upload rejected: Unidentified image error (invalid magic bytes)")
            raise ValidationError("Invalid image file.")
        except Exception as e:
            logger.warning(f"File upload rejected: Exception during magic bytes validation - {str(e)}")
            raise ValidationError("Failed to validate image file.")
        finally:
            # Reset file pointer to beginning for subsequent reads
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

        return file_format

    def validate(self, file_obj):
        """Run all validations and return a dictionary on success."""
        # Handle regular file object without those attributes as well.
        filename = getattr(file_obj, 'name', 'unknown.jpg')
        content_type = getattr(file_obj, 'content_type', 'image/jpeg') # Fallback if not an UploadedFile
        file_size = getattr(file_obj, 'size', -1)

        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        if file_size == -1:
            # Attempt to determine size by seeking
            current_pos = file_obj.tell()
            file_obj.seek(0, os.SEEK_END)
            file_size = file_obj.tell()
            file_obj.seek(current_pos)

        ext = self.validate_extension(filename)
        self.validate_content_type(content_type)
        self.validate_file_size(file_size)
        file_format = self.validate_magic_bytes(file_obj, ext)
        
        return {
            'format': file_format,
            'valid': True
        }
