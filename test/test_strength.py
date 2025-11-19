import pytest
from kcpwd.strength import (
    check_password_strength,
    PasswordStrength,
    get_strength_color,
    get_strength_bar
)


def test_very_weak_password():
    """Test very weak password detection"""
    result = check_password_strength("123")
    assert result['strength'] == PasswordStrength.VERY_WEAK
    assert result['score'] < 30
    assert len(result['feedback']) > 0


def test_weak_password():
    """Test weak password detection"""
    result = check_password_strength("password")
    assert result['strength'] in [PasswordStrength.VERY_WEAK, PasswordStrength.WEAK]
    assert 'common words' in ' '.join(result['feedback']).lower()

def test_strong_password():
    """Test strong password detection"""
    result = check_password_strength("MyP@ssw0rd123")
    assert result['strength'] in [PasswordStrength.MEDIUM, PasswordStrength.STRONG]
    assert result['score'] >= 50


def test_very_strong_password():
    """Test very strong password detection"""
    result = check_password_strength("Xk9#mP2$nQ5@rT8&vW3!")
    assert result['strength'] in [PasswordStrength.STRONG, PasswordStrength.VERY_STRONG]
    assert result['score'] >= 70


def test_empty_password():
    """Test empty password"""
    result = check_password_strength("")
    assert result['score'] == 0
    assert result['strength'] == PasswordStrength.VERY_WEAK
    assert 'empty' in ' '.join(result['feedback']).lower()


def test_length_scoring():
    """Test that longer passwords get better scores"""
    short = check_password_strength("Aa1!")
    medium = check_password_strength("Aa1!Aa1!Aa1!")
    long = check_password_strength("Aa1!Aa1!Aa1!Aa1!Aa1!")

    assert short['score'] < medium['score']
    assert medium['score'] < long['score']


def test_character_variety():
    """Test character variety detection"""
    result = check_password_strength("Abc123!@#")

    assert result['details']['has_lowercase'] == True
    assert result['details']['has_uppercase'] == True
    assert result['details']['has_digits'] == True
    assert result['details']['has_symbols'] == True


def test_missing_character_types():
    """Test feedback for missing character types"""
    result = check_password_strength("onlylowercase")

    feedback_text = ' '.join(result['feedback']).lower()
    assert 'uppercase' in feedback_text or 'capital' in feedback_text


def test_repeated_characters_penalty():
    """Test penalty for repeated characters"""
    normal = check_password_strength("Abc123!@#def")
    repeated = check_password_strength("Aaaa123!@#def")

    # Repeated should have lower score or specific feedback
    assert repeated['score'] <= normal['score'] or \
           any('repeat' in fb.lower() for fb in repeated['feedback'])


def test_sequential_pattern_penalty():
    """Test penalty for sequential patterns"""
    result = check_password_strength("Abc123!@#")

    # Should detect '123' pattern
    feedback_text = ' '.join(result['feedback']).lower()
    assert 'sequential' in feedback_text or result['score'] < 90


def test_common_password_penalty():
    """Test penalty for common passwords"""
    result = check_password_strength("password123")

    feedback_text = ' '.join(result['feedback']).lower()
    assert 'common' in feedback_text or result['score'] < 40


def test_strength_color_mapping():
    """Test color mapping for different strengths"""
    assert get_strength_color(PasswordStrength.VERY_WEAK) == 'red'
    assert get_strength_color(PasswordStrength.WEAK) == 'red'
    assert get_strength_color(PasswordStrength.MEDIUM) == 'yellow'
    assert get_strength_color(PasswordStrength.STRONG) == 'green'
    assert get_strength_color(PasswordStrength.VERY_STRONG) == 'green'


def test_strength_bar_generation():
    """Test visual strength bar generation"""
    # Test different scores
    bar_0 = get_strength_bar(0, width=10)
    bar_50 = get_strength_bar(50, width=10)
    bar_100 = get_strength_bar(100, width=10)

    assert len(bar_0) == 10
    assert len(bar_50) == 10
    assert len(bar_100) == 10

    # Bar should have more filled characters as score increases
    assert bar_0.count('█') < bar_50.count('█')
    assert bar_50.count('█') < bar_100.count('█')


def test_all_character_types_bonus():
    """Test bonus for using all character types"""
    all_types = check_password_strength("Abc123!@#")
    three_types = check_password_strength("Abc123xyz")

    # All types should score better
    assert all_types['score'] >= three_types['score']


def test_score_boundaries():
    """Test that score stays within 0-100"""
    # Very weak password
    result1 = check_password_strength("a")
    assert 0 <= result1['score'] <= 100

    # Very strong password
    result2 = check_password_strength("Xk9#mP2$nQ5@rT8&vW3!zY6%bN4^")
    assert 0 <= result2['score'] <= 100


def test_strength_text_values():
    """Test that strength_text is set correctly"""
    weak = check_password_strength("abc")
    strong = check_password_strength("Xk9#mP2$nQ5@rT8&")

    assert weak['strength_text'] in ['VERY WEAK', 'WEAK']
    assert strong['strength_text'] in ['STRONG', 'VERY STRONG']


def test_positive_feedback():
    """Test that good passwords get positive feedback"""
    result = check_password_strength("Xk9#mP2$nQ5@rT8&vW3!")

    # Should have minimal feedback or positive message
    feedback_text = ' '.join(result['feedback']).lower()
    assert 'looks good' in feedback_text or len(result['feedback']) <= 2