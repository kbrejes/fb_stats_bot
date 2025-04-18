"""
Test script for the new localization system.
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project directory to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the localization module
from src.utils.localization import (
    get_text,
    get_language,
    set_language,
    get_language_name,
    get_available_languages,
    _
)

def test_loading():
    """Test if translations are loaded correctly."""
    # Get available languages
    languages = get_available_languages()
    logger.info(f"Available languages: {languages}")
    
    # Get language names
    for lang in languages:
        name = get_language_name(lang)
        logger.info(f"Language {lang}: {name}")
    
    return True

def test_translations():
    """Test if translations work correctly."""
    success = True
    
    # Test simple translation
    welcome_ru = get_text("welcome", lang="ru", category="common")
    welcome_en = get_text("welcome", lang="en", category="common")
    
    logger.info(f"Russian welcome: {welcome_ru[:30]}...")
    logger.info(f"English welcome: {welcome_en[:30]}...")
    
    if "Добро пожаловать" not in welcome_ru:
        logger.error("Russian welcome translation failed")
        success = False
    
    if "Welcome to the Facebook" not in welcome_en:
        logger.error("English welcome translation failed")
        success = False
    
    # Test translation with formatting
    error_ru = get_text("api_error", lang="ru", category="errors", message="Test error")
    error_en = get_text("api_error", lang="en", category="errors", message="Test error")
    
    logger.info(f"Russian error: {error_ru}")
    logger.info(f"English error: {error_en}")
    
    if "Ошибка API: Test error" != error_ru:
        logger.error("Russian formatted error translation failed")
        success = False
    
    if "API Error: Test error" != error_en:
        logger.error("English formatted error translation failed")
        success = False
    
    # Test short alias _()
    back_ru = _("back", lang="ru", category="menu")
    back_en = _("back", lang="en", category="menu")
    
    logger.info(f"Russian back: {back_ru}")
    logger.info(f"English back: {back_en}")
    
    if "Назад" != back_ru:
        logger.error("Russian back translation via _ alias failed")
        success = False
    
    if "Back" != back_en:
        logger.error("English back translation via _ alias failed")
        success = False
    
    return success

def test_missing_key():
    """Test behavior with missing keys."""
    # Test non-existent key
    nonexistent = get_text("nonexistent_key", lang="ru")
    logger.info(f"Non-existent key translation: {nonexistent}")
    
    # Should return the key itself
    if nonexistent != "nonexistent_key":
        logger.error("Missing key handling failed")
        return False
    
    return True

def test_category_search():
    """Test searching in specific category vs all categories."""
    # First with specific category
    with_category = get_text("main_menu", lang="ru", category="menu")
    
    # Then without category (should search all)
    without_category = get_text("main_menu", lang="ru")
    
    logger.info(f"With category: {with_category}")
    logger.info(f"Without category: {without_category}")
    
    # Should be the same result
    if with_category != without_category:
        logger.error("Category search failed")
        return False
    
    return True

def main():
    """Run all tests."""
    tests = [
        ("Loading translations", test_loading),
        ("Basic translations", test_translations),
        ("Missing key behavior", test_missing_key),
        ("Category search", test_category_search)
    ]
    
    results = []
    
    logger.info("=== LOCALIZATION SYSTEM TESTS ===")
    
    for name, test_func in tests:
        logger.info(f"\n--- Testing: {name} ---")
        try:
            success = test_func()
            results.append((name, success))
            status = "PASSED" if success else "FAILED"
            logger.info(f"--- {name}: {status} ---")
        except Exception as e:
            logger.error(f"Exception in {name}: {str(e)}")
            results.append((name, False))
            logger.info(f"--- {name}: FAILED (exception) ---")
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Passed: {passed}/{total} tests")
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} - {name}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 