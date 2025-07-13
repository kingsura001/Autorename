"""
Template parser for file renaming
"""

import re
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class TemplateParser:
    """Parser for rename templates with variable substitution"""
    
    def __init__(self, template: str):
        self.template = template
        self.variables = {
            'title': self._extract_title,
            'season': self._extract_season,
            'episode': self._extract_episode,
            'year': self._extract_year,
            'quality': self._extract_quality,
            'resolution': self._extract_resolution,
            'codec': self._extract_codec,
            'source': self._extract_source,
            'group': self._extract_group,
            'extension': self._extract_extension
        }
        
        # Common patterns for extraction
        self.patterns = {
            'season_episode': [
                r'[Ss](\d{1,2})[Ee](\d{1,2})',
                r'[Ss](\d{1,2})\s*[Ee](\d{1,2})',
                r'(\d{1,2})[xX](\d{1,2})',
                r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})',
                r'S(\d{1,2})E(\d{1,2})'
            ],
            'year': [
                r'(\d{4})',
                r'\((\d{4})\)',
                r'\.(\d{4})\.',
                r'\s(\d{4})\s'
            ],
            'quality': [
                r'(\d{3,4}[pi])',
                r'(720p|1080p|1440p|2160p|480p|360p)',
                r'(HD|FHD|4K|UHD|SD)',
                r'(BluRay|BRRip|DVDRip|WEBRip|HDTV|WEB-DL)'
            ],
            'resolution': [
                r'(\d{3,4}x\d{3,4})',
                r'(\d{3,4}p)',
                r'(720p|1080p|1440p|2160p|480p|360p)'
            ],
            'codec': [
                r'(x264|x265|h264|h265|HEVC|AVC|XviD|DivX)',
                r'(H\.264|H\.265)',
                r'(MPEG-4|MPEG-2)'
            ],
            'source': [
                r'(BluRay|BRRip|DVDRip|WEBRip|HDTV|WEB-DL|CAM|TS|TC|R5|SCR)',
                r'(Blu-ray|DVD|WEB|HDTV|TV)'
            ],
            'group': [
                r'-([A-Za-z0-9]+)$',
                r'\.([A-Za-z0-9]+)$',
                r'\[([A-Za-z0-9]+)\]$',
                r'\{([A-Za-z0-9]+)\}$'
            ]
        }
    
    def parse(self, filename: str) -> str:
        """
        Parse filename using template
        
        Args:
            filename: Original filename
            
        Returns:
            Parsed filename using template
        """
        try:
            # Extract file extension
            file_path = Path(filename)
            name_without_ext = file_path.stem
            extension = file_path.suffix
            
            # Parse template
            result = self.template
            
            # Find all template variables
            template_vars = re.findall(r'\{([^}]+)\}', self.template)
            
            # Extract values from filename
            extracted_values = self._extract_all_values(name_without_ext)
            
            # Replace variables in template
            for var in template_vars:
                if var in self.variables:
                    value = extracted_values.get(var, '')
                    
                    # Format value based on variable type
                    formatted_value = self._format_value(var, value)
                    
                    # Replace in template
                    result = result.replace(f'{{{var}}}', formatted_value)
                else:
                    # Unknown variable, remove it
                    result = result.replace(f'{{{var}}}', '')
            
            # Clean up result
            result = self._clean_result(result)
            
            # Add extension back
            if extension:
                result += extension
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing template: {e}")
            # Return original filename on error
            return filename
    
    def _extract_all_values(self, filename: str) -> Dict[str, Any]:
        """Extract all possible values from filename"""
        values = {}
        
        # Clean filename for parsing
        clean_name = self._clean_filename(filename)
        
        # Extract each variable
        for var_name, extract_func in self.variables.items():
            try:
                values[var_name] = extract_func(clean_name)
            except Exception as e:
                logger.debug(f"Error extracting {var_name}: {e}")
                values[var_name] = ''
        
        return values
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename for better parsing"""
        # Replace common separators with spaces
        clean = re.sub(r'[._\-\+]', ' ', filename)
        
        # Remove multiple spaces
        clean = re.sub(r'\s+', ' ', clean)
        
        return clean.strip()
    
    def _extract_title(self, filename: str) -> str:
        """Extract title from filename"""
        try:
            # Try to find title before season/episode pattern
            for pattern in self.patterns['season_episode']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    title = filename[:match.start()].strip()
                    if title:
                        return self._clean_title(title)
            
            # Try to find title before year
            for pattern in self.patterns['year']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    title = filename[:match.start()].strip()
                    if title:
                        return self._clean_title(title)
            
            # Try to find title before quality indicator
            for pattern in self.patterns['quality']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    title = filename[:match.start()].strip()
                    if title:
                        return self._clean_title(title)
            
            # If no patterns found, use the whole filename
            return self._clean_title(filename)
            
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
            return filename
    
    def _clean_title(self, title: str) -> str:
        """Clean extracted title"""
        # Replace separators with spaces
        title = re.sub(r'[._\-\+]', ' ', title)
        
        # Remove multiple spaces
        title = re.sub(r'\s+', ' ', title)
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(the|a|an)\s+', '', title, flags=re.IGNORECASE)
        
        return title.strip()
    
    def _extract_season(self, filename: str) -> str:
        """Extract season from filename"""
        try:
            for pattern in self.patterns['season_episode']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    season = int(match.group(1))
                    return f"S{season:02d}"
            
            # Try alternative season patterns
            season_patterns = [
                r'Season\s*(\d{1,2})',
                r'Series\s*(\d{1,2})',
                r'S(\d{1,2})',
                r'(\d{1,2})x\d{1,2}'
            ]
            
            for pattern in season_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    season = int(match.group(1))
                    return f"S{season:02d}"
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting season: {e}")
            return ""
    
    def _extract_episode(self, filename: str) -> str:
        """Extract episode from filename"""
        try:
            for pattern in self.patterns['season_episode']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    episode = int(match.group(2))
                    return f"E{episode:02d}"
            
            # Try alternative episode patterns
            episode_patterns = [
                r'Episode\s*(\d{1,2})',
                r'Ep\s*(\d{1,2})',
                r'E(\d{1,2})',
                r'\d{1,2}x(\d{1,2})'
            ]
            
            for pattern in episode_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    episode = int(match.group(1))
                    return f"E{episode:02d}"
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting episode: {e}")
            return ""
    
    def _extract_year(self, filename: str) -> str:
        """Extract year from filename"""
        try:
            for pattern in self.patterns['year']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    year = int(match.group(1))
                    # Validate year range
                    if 1900 <= year <= 2100:
                        return str(year)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting year: {e}")
            return ""
    
    def _extract_quality(self, filename: str) -> str:
        """Extract quality from filename"""
        try:
            for pattern in self.patterns['quality']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    quality = match.group(1).upper()
                    
                    # Normalize quality names
                    quality_map = {
                        'HD': '720p',
                        'FHD': '1080p',
                        '4K': '2160p',
                        'UHD': '2160p',
                        'SD': '480p',
                        'BLUYRAY': 'BluRay',
                        'BRRIP': 'BRRip',
                        'DVDRIP': 'DVDRip',
                        'WEBRIP': 'WEBRip',
                        'WEB-DL': 'WEB-DL'
                    }
                    
                    return quality_map.get(quality, quality)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting quality: {e}")
            return ""
    
    def _extract_resolution(self, filename: str) -> str:
        """Extract resolution from filename"""
        try:
            for pattern in self.patterns['resolution']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting resolution: {e}")
            return ""
    
    def _extract_codec(self, filename: str) -> str:
        """Extract codec from filename"""
        try:
            for pattern in self.patterns['codec']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    codec = match.group(1).upper()
                    
                    # Normalize codec names
                    codec_map = {
                        'H.264': 'H264',
                        'H.265': 'H265',
                        'HEVC': 'H265',
                        'AVC': 'H264',
                        'MPEG-4': 'MP4',
                        'MPEG-2': 'MP2'
                    }
                    
                    return codec_map.get(codec, codec)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting codec: {e}")
            return ""
    
    def _extract_source(self, filename: str) -> str:
        """Extract source from filename"""
        try:
            for pattern in self.patterns['source']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    source = match.group(1)
                    
                    # Normalize source names
                    source_map = {
                        'Blu-ray': 'BluRay',
                        'DVD': 'DVDRip',
                        'WEB': 'WEB-DL',
                        'TV': 'HDTV'
                    }
                    
                    return source_map.get(source, source)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting source: {e}")
            return ""
    
    def _extract_group(self, filename: str) -> str:
        """Extract release group from filename"""
        try:
            for pattern in self.patterns['group']:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting group: {e}")
            return ""
    
    def _extract_extension(self, filename: str) -> str:
        """Extract file extension"""
        try:
            return Path(filename).suffix
        except Exception as e:
            logger.error(f"Error extracting extension: {e}")
            return ""
    
    def _format_value(self, var_name: str, value: Any) -> str:
        """Format value based on variable type"""
        if not value:
            return ""
        
        # Convert to string
        str_value = str(value)
        
        # Apply specific formatting based on variable
        if var_name in ['season', 'episode']:
            # Already formatted in extraction
            return str_value
        elif var_name == 'title':
            # Title case for titles
            return str_value.title()
        elif var_name == 'year':
            # Ensure 4 digits
            return str_value.zfill(4) if str_value.isdigit() else str_value
        else:
            return str_value
    
    def _clean_result(self, result: str) -> str:
        """Clean final result"""
        # Remove multiple spaces
        result = re.sub(r'\s+', ' ', result)
        
        # Remove leading/trailing spaces and separators
        result = result.strip(' .-_')
        
        # Remove empty brackets/parentheses
        result = re.sub(r'\[\s*\]', '', result)
        result = re.sub(r'\(\s*\)', '', result)
        result = re.sub(r'\{\s*\}', '', result)
        
        # Clean up multiple separators
        result = re.sub(r'[-_.]{2,}', '-', result)
        
        return result.strip()
    
    def validate_template(self, template: str) -> tuple[bool, str]:
        """
        Validate template syntax
        
        Args:
            template: Template string to validate
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Check for balanced braces
            open_braces = template.count('{')
            close_braces = template.count('}')
            
            if open_braces != close_braces:
                return False, "Unbalanced braces in template"
            
            # Check for valid variables
            template_vars = re.findall(r'\{([^}]+)\}', template)
            
            for var in template_vars:
                if var not in self.variables:
                    return False, f"Unknown variable: {var}"
            
            # Try to parse with test filename
            test_filename = "Test.Movie.2024.1080p.BluRay.x264-GROUP.mkv"
            result = self.parse(test_filename)
            
            if not result:
                return False, "Template produces empty result"
            
            return True, "Template is valid"
            
        except Exception as e:
            return False, f"Template validation error: {str(e)}"
    
    def get_available_variables(self) -> Dict[str, str]:
        """Get available template variables with descriptions"""
        return {
            "title": "Original filename without extension",
            "season": "Season number (S01, S02, etc.)",
            "episode": "Episode number (E01, E02, etc.)",
            "year": "Year from filename (2024, 2025, etc.)",
            "quality": "Quality indicator (1080p, 720p, BluRay, etc.)",
            "resolution": "Video resolution (1920x1080, 1280x720, etc.)",
            "codec": "Video codec (H264, H265, x264, etc.)",
            "source": "Source type (BluRay, WEB-DL, HDTV, etc.)",
            "group": "Release group name",
            "extension": "File extension (.mkv, .mp4, etc.)"
        }
    
    def generate_suggestions(self, filename: str) -> list[str]:
        """Generate template suggestions based on filename"""
        suggestions = []
        
        # Extract values to see what's available
        extracted = self._extract_all_values(filename)
        
        # Basic suggestions
        suggestions.append("{title}")
        
        # Season/Episode based suggestions
        if extracted.get('season') and extracted.get('episode'):
            suggestions.extend([
                "{title} - {season}{episode}",
                "{title} {season}{episode}",
                "{title} - {season}{episode} - {quality}",
                "{title} [{season}{episode}] {quality}"
            ])
        
        # Movie suggestions
        if extracted.get('year'):
            suggestions.extend([
                "{title} ({year})",
                "{title} ({year}) [{quality}]",
                "{title} - {year} - {quality}",
                "{title} ({year}) {quality} {codec}"
            ])
        
        # Quality based suggestions
        if extracted.get('quality'):
            suggestions.extend([
                "{title} [{quality}]",
                "{title} - {quality}",
                "{title} ({year}) [{quality}]"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:10]  # Return top 10 suggestions
