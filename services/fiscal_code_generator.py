"""
Fiscal Code Generation Service
Integrates with extractCF.py to generate Italian fiscal codes from patient data
"""

import re
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from rapidfuzz import fuzz, process

# Import the fiscal code calculation function and cadastral codes
from extractCF import calculate_tax_code, cadastral_codes


class FiscalCodeGenerator:
    """Service for generating Italian fiscal codes from patient data"""

    def __init__(self):
        # Create reverse lookup dictionary (city name -> code)
        self.city_to_code = {city.upper(): code for code, city in cadastral_codes.items()}
        logger.info(f"🏛️ Loaded {len(self.city_to_code)} Italian cities for fiscal code generation")

    def normalize_city_name(self, city_name: str) -> str:
        """
        Normalize city name for better matching

        Args:
            city_name: Raw city name from user input

        Returns:
            Normalized city name
        """
        if not city_name:
            return ""

        # Convert to uppercase and strip whitespace
        normalized = city_name.strip().upper()

        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(COMUNE DI|CITTA DI|BORGO|FRAZIONE)\s+', '', normalized)
        normalized = re.sub(r'\s+(PAESE|COMUNE|CITTA|CENTRO)$', '', normalized)

        # Remove accents and special characters (simple approach)
        accent_map = {
            'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
            'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
            'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
            'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
            'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
            'Ç': 'C', 'Ñ': 'N'
        }

        for accented, plain in accent_map.items():
            normalized = normalized.replace(accented, plain)

        return normalized

    def find_city_code(self, city_name: str, threshold: int = 80) -> Optional[Tuple[str, str, int]]:
        """
        Find cadastral code for a city using fuzzy matching

        Args:
            city_name: City name to search for
            threshold: Minimum similarity score (0-100)

        Returns:
            Tuple of (cadastral_code, matched_city_name, similarity_score) or None
        """
        if not city_name:
            return None

        normalized_input = self.normalize_city_name(city_name)
        logger.debug(f"🔍 Searching for city: '{city_name}' -> normalized: '{normalized_input}'")

        # First try exact match
        if normalized_input in self.city_to_code:
            code = self.city_to_code[normalized_input]
            logger.success(f"✅ Exact match found: {normalized_input} -> {code}")
            return code, normalized_input, 100

        # Try fuzzy matching
        try:
            # Get all city names for fuzzy matching
            city_names = list(self.city_to_code.keys())

            # Find best matches
            matches = process.extract(
                normalized_input,
                city_names,
                scorer=fuzz.ratio,
                limit=5
            )

            if matches and matches[0][1] >= threshold:
                best_match = matches[0]
                matched_city = best_match[0]
                score = best_match[1]
                code = self.city_to_code[matched_city]

                logger.success(f"✅ Fuzzy match found: '{city_name}' -> '{matched_city}' ({score}%) -> {code}")
                return code, matched_city, score
            else:
                best_score = matches[0][1] if matches else 0
                logger.warning(f"❌ No good match found for '{city_name}' (best score: {best_score}%)")
                return None

        except Exception as e:
            logger.error(f"❌ Error in fuzzy matching: {e}")
            return None

    def generate_fiscal_code(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fiscal code from patient data

        Args:
            patient_data: Dictionary containing:
                - name: First name
                - surname: Last name
                - birth_date: Birth date in YYYY-MM-DD format
                - gender: Gender ('m' or 'f')
                - birth_city: Birth city name

        Returns:
            Dictionary with generation result
        """
        try:
            # Extract required fields
            first_name = patient_data.get('name', '').strip()
            last_name = patient_data.get('surname', '').strip()
            birth_date = patient_data.get('birth_date', '').strip()
            gender = patient_data.get('gender', '').lower().strip()
            birth_city = patient_data.get('birth_city', '').strip()

            # Validate required fields
            if not all([first_name, last_name, birth_date, gender, birth_city]):
                missing_fields = [field for field, value in {
                    'name': first_name,
                    'surname': last_name,
                    'birth_date': birth_date,
                    'gender': gender,
                    'birth_city': birth_city
                }.items() if not value]

                return {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "fiscal_code": None
                }

            # Normalize gender
            if gender not in ['m', 'f']:
                return {
                    "success": False,
                    "error": f"Invalid gender: {gender}. Must be 'm' or 'f'",
                    "fiscal_code": None
                }

            # Find city code
            city_result = self.find_city_code(birth_city)
            if not city_result:
                return {
                    "success": False,
                    "error": f"City '{birth_city}' not found in Italian cadastral registry",
                    "fiscal_code": None,
                    "suggestions": self._get_city_suggestions(birth_city)
                }

            city_code, matched_city, similarity = city_result

            # Validate date format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', birth_date):
                return {
                    "success": False,
                    "error": f"Invalid date format: {birth_date}. Expected YYYY-MM-DD",
                    "fiscal_code": None
                }

            logger.info(f"🔧 Generating fiscal code for: {first_name} {last_name}, "
                       f"born {birth_date} in {matched_city} ({gender.upper()})")

            # Generate fiscal code using the imported function
            fiscal_code = calculate_tax_code(
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=gender.upper(),
                birth_city=city_code
            )

            logger.success(f"✅ Generated fiscal code: {fiscal_code}")

            return {
                "success": True,
                "fiscal_code": fiscal_code,
                "city_code": city_code,
                "matched_city": matched_city,
                "similarity_score": similarity,
                "generation_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": birth_date,
                    "gender": gender.upper(),
                    "birth_city": matched_city,
                    "city_code": city_code
                }
            }

        except Exception as e:
            logger.error(f"❌ Fiscal code generation error: {e}")
            return {
                "success": False,
                "error": f"Generation failed: {str(e)}",
                "fiscal_code": None
            }

    def _get_city_suggestions(self, city_name: str, limit: int = 3) -> list:
        """Get city name suggestions for failed matches"""
        try:
            normalized_input = self.normalize_city_name(city_name)
            city_names = list(self.city_to_code.keys())

            matches = process.extract(
                normalized_input,
                city_names,
                scorer=fuzz.ratio,
                limit=limit
            )

            return [match[0] for match in matches if match[1] > 50]
        except:
            return []

    def validate_fiscal_code(self, fiscal_code: str) -> Dict[str, Any]:
        """
        Basic validation of fiscal code format

        Args:
            fiscal_code: Fiscal code to validate

        Returns:
            Validation result dictionary
        """
        if not fiscal_code or len(fiscal_code) != 16:
            return {
                "valid": False,
                "error": "Fiscal code must be exactly 16 characters"
            }

        # Check format: 6 letters + 2 digits + 1 letter + 2 digits + 1 letter + 3 chars + 1 letter
        pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        if not re.match(pattern, fiscal_code.upper()):
            return {
                "valid": False,
                "error": "Invalid fiscal code format"
            }

        return {
            "valid": True,
            "fiscal_code": fiscal_code.upper()
        }


# Global instance
fiscal_code_generator = FiscalCodeGenerator()