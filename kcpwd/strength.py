"""
kcpwd.strength - Password strength analysis
"""

import re
from typing import Dict, Tuple
from enum import Enum


class PasswordStrength(Enum):
    """Password strength levels"""
    VERY_WEAK = 0
    WEAK = 1
    MEDIUM = 2
    STRONG = 3
    VERY_STRONG = 4


def check_password_strength(password: str) -> Dict[str, any]:
    """Analyze password strength and return detailed metrics

    Args:
        password: Password to analyze

    Returns:
        dict: Contains 'score', 'strength', 'feedback', 'details'
    """
    if not password:
        return {
            'score': 0,
            'strength': PasswordStrength.VERY_WEAK,
            'feedback': ['Password cannot be empty'],
            'details': {}
        }

    score = 0
    feedback = []
    details = {}

    # Length scoring
    length = len(password)
    details['length'] = length

    if length < 8:
        feedback.append('Password should be at least 8 characters')
        score += length * 2
    elif length < 12:
        score += 20
    elif length < 16:
        score += 25
    else:
        score += 30

    # Character variety
    has_lowercase = bool(re.search(r'[a-z]', password))
    has_uppercase = bool(re.search(r'[A-Z]', password))
    has_digits = bool(re.search(r'\d', password))
    has_symbols = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password))

    details['has_lowercase'] = has_lowercase
    details['has_uppercase'] = has_uppercase
    details['has_digits'] = has_digits
    details['has_symbols'] = has_symbols

    char_variety = sum([has_lowercase, has_uppercase, has_digits, has_symbols])
    score += char_variety * 10

    if not has_lowercase:
        feedback.append('Add lowercase letters')
    if not has_uppercase:
        feedback.append('Add uppercase letters')
    if not has_digits:
        feedback.append('Add numbers')
    if not has_symbols:
        feedback.append('Add special characters (!@#$%^&*...)')

    # Complexity bonus
    if char_variety == 4:
        score += 20

    # Penalize common patterns
    if re.search(r'(.)\1{2,}', password):
        score -= 10
        feedback.append('Avoid repeated characters (aaa, 111, etc.)')

    if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde)', password.lower()):
        score -= 10
        feedback.append('Avoid sequential patterns (123, abc, etc.)')

    # Common weak passwords
    common_weak = ['password', 'pass', '1234', 'qwerty', 'admin', 'letmein', 'welcome']
    if any(weak in password.lower() for weak in common_weak):
        score -= 20
        feedback.append('Avoid common words like "password", "admin", "123"')

    # Cap score between 0-100
    score = max(0, min(100, score))

    # Determine strength level
    if score < 30:
        strength = PasswordStrength.VERY_WEAK
        strength_text = 'VERY WEAK'
    elif score < 50:
        strength = PasswordStrength.WEAK
        strength_text = 'WEAK'
    elif score < 70:
        strength = PasswordStrength.MEDIUM
        strength_text = 'MEDIUM'
    elif score < 85:
        strength = PasswordStrength.STRONG
        strength_text = 'STRONG'
    else:
        strength = PasswordStrength.VERY_STRONG
        strength_text = 'VERY STRONG'

    return {
        'score': score,
        'strength': strength,
        'strength_text': strength_text,
        'feedback': feedback if feedback else ['Password looks good!'],
        'details': details
    }


def get_strength_color(strength: PasswordStrength) -> str:
    """Get color for CLI display based on strength"""
    color_map = {
        PasswordStrength.VERY_WEAK: 'red',
        PasswordStrength.WEAK: 'red',
        PasswordStrength.MEDIUM: 'yellow',
        PasswordStrength.STRONG: 'green',
        PasswordStrength.VERY_STRONG: 'green'
    }
    return color_map.get(strength, 'white')


def get_strength_bar(score: int, width: int = 20) -> str:
    """Generate a visual strength bar"""
    filled = int((score / 100) * width)
    empty = width - filled
    return '█' * filled + '░' * empty