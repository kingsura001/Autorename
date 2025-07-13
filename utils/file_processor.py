"""
File processing utilities for renaming and media operations
"""

import os
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image

from config import Config
from database.models import UserSettings

logger = logging.getLogger(__name__)

class FileProcessor:
    """File processing class for handling various file operations"""
    
    def __init__(self):
        self.supported_video_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        self.supported_audio_formats = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a']
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
    async def process_file(self, input_path: str, new_name: str, file_type: str, settings: Optional[UserSettings] = None) -> str:
        """
        Process a file with the given parameters
        
        Args:
            input_path: Path to input file
            new_name: New filename
            file_type: Type of file (video, audio, document)
            settings: User settings for processing
            
        Returns:
            Path to processed file
        """
        try:
            # Ensure output directory exists
            output_dir = Config.UPLOAD_PATH
            os.makedirs(output_dir, exist_ok=True)
            
            # Get file extension
            file_extension = Path(input_path).suffix.lower()
            
            # Ensure new name has extension
            if not new_name.endswith(file_extension):
                new_name += file_extension
            
            output_path = os.path.join(output_dir, new_name)
            
            # Process based on file type
            if file_type == "video":
                return await self._process_video(input_path, output_path, settings)
            elif file_type == "audio":
                return await self._process_audio(input_path, output_path, settings)
            else:
                return await self._process_document(input_path, output_path, settings)
                
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            raise
    
    async def _process_video(self, input_path: str, output_path: str, settings: Optional[UserSettings] = None) -> str:
        """Process video file"""
        try:
            file_extension = Path(input_path).suffix.lower()
            
            # Check if we need to apply thumbnail or quality changes
            if settings and (settings.default_thumbnail or settings.quality_preference != "original"):
                return await self._process_video_with_ffmpeg(input_path, output_path, settings)
            else:
                # Simple rename/copy
                shutil.copy2(input_path, output_path)
                return output_path
                
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise
    
    async def _process_video_with_ffmpeg(self, input_path: str, output_path: str, settings: UserSettings) -> str:
        """Process video using FFmpeg"""
        try:
            cmd = [Config.FFMPEG_PATH, "-i", input_path]
            
            # Add thumbnail if specified
            if settings.default_thumbnail:
                thumbnail_path = os.path.join(Config.THUMBNAIL_PATH, settings.default_thumbnail)
                if os.path.exists(thumbnail_path):
                    cmd.extend(["-i", thumbnail_path])
                    cmd.extend(["-map", "0", "-map", "1", "-c", "copy", "-disposition:v:1", "attached_pic"])
            
            # Apply quality settings
            if settings.quality_preference != "original":
                quality_map = {
                    "high": ["-crf", "18", "-preset", "medium"],
                    "medium": ["-crf", "23", "-preset", "medium"],
                    "low": ["-crf", "28", "-preset", "fast"]
                }
                
                if settings.quality_preference in quality_map:
                    cmd.extend(["-c:v", "libx264"])
                    cmd.extend(quality_map[settings.quality_preference])
            else:
                cmd.extend(["-c", "copy"])
            
            cmd.extend(["-y", output_path])
            
            # Execute FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                # Fallback to simple copy
                shutil.copy2(input_path, output_path)
            
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg processing timed out")
            shutil.copy2(input_path, output_path)
            return output_path
        except Exception as e:
            logger.error(f"Error processing video with FFmpeg: {e}")
            shutil.copy2(input_path, output_path)
            return output_path
    
    async def _process_audio(self, input_path: str, output_path: str, settings: Optional[UserSettings] = None) -> str:
        """Process audio file"""
        try:
            # Check if we need to apply quality changes
            if settings and settings.quality_preference != "original":
                return await self._process_audio_with_ffmpeg(input_path, output_path, settings)
            else:
                # Simple rename/copy
                shutil.copy2(input_path, output_path)
                return output_path
                
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise
    
    async def _process_audio_with_ffmpeg(self, input_path: str, output_path: str, settings: UserSettings) -> str:
        """Process audio using FFmpeg"""
        try:
            cmd = [Config.FFMPEG_PATH, "-i", input_path]
            
            # Apply quality settings
            if settings.quality_preference != "original":
                quality_map = {
                    "high": ["-q:a", "0"],
                    "medium": ["-q:a", "2"],
                    "low": ["-q:a", "4"]
                }
                
                if settings.quality_preference in quality_map:
                    cmd.extend(quality_map[settings.quality_preference])
            else:
                cmd.extend(["-c", "copy"])
            
            cmd.extend(["-y", output_path])
            
            # Execute FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                # Fallback to simple copy
                shutil.copy2(input_path, output_path)
            
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg processing timed out")
            shutil.copy2(input_path, output_path)
            return output_path
        except Exception as e:
            logger.error(f"Error processing audio with FFmpeg: {e}")
            shutil.copy2(input_path, output_path)
            return output_path
    
    async def _process_document(self, input_path: str, output_path: str, settings: Optional[UserSettings] = None) -> str:
        """Process document file"""
        try:
            # For documents, we just rename/copy
            shutil.copy2(input_path, output_path)
            return output_path
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            file_stats = os.stat(file_path)
            file_extension = Path(file_path).suffix.lower()
            
            info = {
                "size": file_stats.st_size,
                "extension": file_extension,
                "created": file_stats.st_ctime,
                "modified": file_stats.st_mtime,
                "is_video": file_extension in self.supported_video_formats,
                "is_audio": file_extension in self.supported_audio_formats,
                "is_image": file_extension in self.supported_image_formats
            }
            
            # Get additional info for media files
            if info["is_video"] or info["is_audio"]:
                media_info = self._get_media_info(file_path)
                info.update(media_info)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {"error": str(e)}
    
    def _get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get media file information using FFprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                probe_data = json.loads(result.stdout)
                
                info = {}
                if "format" in probe_data:
                    format_info = probe_data["format"]
                    info["duration"] = float(format_info.get("duration", 0))
                    info["bitrate"] = int(format_info.get("bit_rate", 0))
                
                if "streams" in probe_data:
                    for stream in probe_data["streams"]:
                        if stream.get("codec_type") == "video":
                            info["width"] = stream.get("width")
                            info["height"] = stream.get("height")
                            info["fps"] = eval(stream.get("r_frame_rate", "0/1"))
                            info["video_codec"] = stream.get("codec_name")
                        elif stream.get("codec_type") == "audio":
                            info["sample_rate"] = stream.get("sample_rate")
                            info["audio_codec"] = stream.get("codec_name")
                
                return info
            else:
                logger.warning(f"FFprobe failed: {result.stderr}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return {}
    
    def validate_file_type(self, file_path: str, expected_type: str) -> bool:
        """Validate file type"""
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if expected_type == "video":
                return file_extension in self.supported_video_formats
            elif expected_type == "audio":
                return file_extension in self.supported_audio_formats
            elif expected_type == "image":
                return file_extension in self.supported_image_formats
            else:
                return True  # Allow all other types as documents
                
        except Exception as e:
            logger.error(f"Error validating file type: {e}")
            return False
    
    def cleanup_temp_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up temp file {file_path}: {e}")
    
    def get_supported_formats(self) -> Dict[str, list]:
        """Get supported file formats"""
        return {
            "video": self.supported_video_formats,
            "audio": self.supported_audio_formats,
            "image": self.supported_image_formats
        }
    
    def estimate_processing_time(self, file_size: int, file_type: str, settings: Optional[UserSettings] = None) -> int:
        """Estimate processing time in seconds"""
        try:
            # Base processing time based on file size (rough estimate)
            base_time = file_size / (10 * 1024 * 1024)  # 10MB per second base rate
            
            # Multiply based on file type and operations
            if file_type == "video":
                if settings and settings.quality_preference != "original":
                    return int(base_time * 5)  # Re-encoding takes longer
                else:
                    return int(base_time * 0.5)  # Simple copy
            elif file_type == "audio":
                if settings and settings.quality_preference != "original":
                    return int(base_time * 2)
                else:
                    return int(base_time * 0.3)
            else:
                return int(base_time * 0.1)  # Documents are quick
                
        except Exception as e:
            logger.error(f"Error estimating processing time: {e}")
            return 60  # Default to 1 minute
