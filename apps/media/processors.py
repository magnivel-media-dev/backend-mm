import io
import time
import logging
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Processor to resize, optimize, and convert images to WebP format."""

    def __init__(self, quality=None, max_dimension=None):
        from django.conf import settings
        self.quality = quality or getattr(settings, 'MEDIA_IMAGE_QUALITY', 80)
        self.max_dimension = max_dimension

    def _convert_to_rgb(self, image):
        """Convert image to RGB mode properly."""
        if image.mode in ('RGBA', 'LA'):
            # Paste onto white background to handle transparency
            background = Image.new('RGB', image.size, (255, 255, 255))
            # Handle alpha channel
            background.paste(image, mask=image.split()[-1])
            return background
        elif image.mode == 'P':
            # Handle palette mode
            if 'transparency' in image.info:
                # Convert to RGBA and then to RGB with white bg
                image = image.convert('RGBA')
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                return background
            else:
                return image.convert('RGB')
        elif image.mode == 'CMYK':
            return image.convert('RGB')
        elif image.mode != 'RGB':
            return image.convert('RGB')
        return image

    def process(self, file_obj):
        """
        Process the image:
        1. Open
        2. Auto-orient EXIF
        3. Convert to RGB
        4. Resize if max_dimension is set
        5. Save to WebP in memory
        6. Return results
        """
        start_time = time.time()

        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)

        # Determine original file size for stats
        original_size = 0
        if hasattr(file_obj, 'size'):
            original_size = file_obj.size
        else:
            current_pos = file_obj.tell()
            file_obj.seek(0, io.SEEK_END)
            original_size = file_obj.tell()
            file_obj.seek(current_pos)

        try:
            with Image.open(file_obj) as img:
                # 2. Auto-orient
                img = ImageOps.exif_transpose(img)
                
                # 3. Convert to RGB
                img = self._convert_to_rgb(img)
                
                # 4. Resize if needed
                if self.max_dimension:
                    width, height = img.size
                    if max(width, height) > self.max_dimension:
                        # Calculate new size while maintaining aspect ratio
                        if width > height:
                            new_width = self.max_dimension
                            new_height = int((self.max_dimension / width) * height)
                        else:
                            new_height = self.max_dimension
                            new_width = int((self.max_dimension / height) * width)
                            
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # 5. Save as WebP
                output_buffer = io.BytesIO()
                img.save(
                    output_buffer,
                    format='WEBP',
                    quality=self.quality,
                    optimize=True,
                    method=4
                )
                
                # 6. Gather stats
                processed_size = output_buffer.tell()
                output_buffer.seek(0)
                width, height = img.size
                
                compression_ratio = processed_size / original_size if original_size > 0 else 0
                time_taken = time.time() - start_time
                
                logger.info(
                    f"Image processed: orig_size={original_size} bytes, "
                    f"new_size={processed_size} bytes, "
                    f"ratio={compression_ratio:.2f}, time={time_taken:.3f}s"
                )

                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)

                return {
                    'buffer': output_buffer,
                    'width': width,
                    'height': height,
                    'size': processed_size,
                    'format': 'webp',
                    'mime_type': 'image/webp'
                }

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            raise
