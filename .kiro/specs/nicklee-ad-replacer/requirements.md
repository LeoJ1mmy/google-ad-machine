# Requirements Document

## Introduction

This feature involves creating a new ad replacement tool specifically designed for the nicklee.tw website. The tool will be based on the existing ad_replacer.py framework but customized for nicklee.tw's specific structure and ad placement patterns. It will maintain all the core functionality including button styles, ad restoration, ad replacement, ad size detection, automatic website crawling, and config.py parameter integration.

## Requirements

### Requirement 1

**User Story:** As a user, I want to create a nicklee.tw-specific ad replacer that inherits all functionality from the base ad_replacer.py, so that I can replace ads on nicklee.tw with my custom images.

#### Acceptance Criteria

1. WHEN the system is initialized THEN it SHALL load all configuration parameters from config.py
2. WHEN the system starts THEN it SHALL support all button styles (dots, cross, adchoices, adchoices_dots, none) as defined in the base system
3. WHEN the system processes a website THEN it SHALL maintain the same ad replacement logic as the base system
4. WHEN the system detects ads THEN it SHALL use the same ad size detection algorithms as the base system
5. WHEN the system completes ad replacement THEN it SHALL support ad restoration functionality identical to the base system

### Requirement 2

**User Story:** As a user, I want the nicklee.tw ad replacer to automatically discover and process articles from nicklee.tw, so that I can efficiently capture screenshots from multiple pages.

#### Acceptance Criteria

1. WHEN the system accesses nicklee.tw THEN it SHALL automatically discover article links using appropriate CSS selectors
2. WHEN article links are found THEN it SHALL filter them to ensure they belong to nicklee.tw domain
3. WHEN processing articles THEN it SHALL respect the NEWS_COUNT parameter from config.py
4. WHEN no articles are found THEN it SHALL provide appropriate error handling and logging
5. WHEN articles are processed THEN it SHALL randomize the selection to avoid predictable patterns

### Requirement 3

**User Story:** As a user, I want the nicklee.tw ad replacer to use the same multi-screen support and screenshot functionality as the base system, so that I can capture high-quality screenshots on my preferred display.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL detect available screens using the ScreenManager class
2. WHEN a screen is selected THEN it SHALL position the browser window correctly on that screen
3. WHEN taking screenshots THEN it SHALL use platform-specific screenshot methods (macOS screencapture, Windows MSS, Linux import)
4. WHEN screenshots are saved THEN it SHALL use the naming convention "nicklee_replaced_{timestamp}.png"
5. WHEN screenshot folder doesn't exist THEN it SHALL create it automatically

### Requirement 4

**User Story:** As a user, I want the nicklee.tw ad replacer to support all the same ad replacement features including button overlays and ad restoration, so that the replaced ads look authentic and professional.

#### Acceptance Criteria

1. WHEN ads are replaced THEN it SHALL support all button styles defined in BUTTON_STYLE config
2. WHEN buttons are added THEN it SHALL position them correctly (close button at top-right, info button offset by 16px)
3. WHEN in "none" mode THEN it SHALL not add any buttons to replaced ads
4. WHEN ads are replaced THEN it SHALL preserve original ad dimensions and positioning
5. WHEN screenshots are taken THEN it SHALL restore original ads after capturing the image

### Requirement 5

**User Story:** As a user, I want the nicklee.tw ad replacer to integrate seamlessly with the existing config.py file, so that I can use the same configuration for all my ad replacement tools.

#### Acceptance Criteria

1. WHEN the system loads THEN it SHALL read all parameters from the existing config.py file
2. WHEN config.py is missing THEN it SHALL fall back to sensible default values
3. WHEN IMAGE_USAGE_COUNT is defined THEN it SHALL respect the usage limits for each image
4. WHEN SCREENSHOT_COUNT is reached THEN it SHALL stop processing and report completion
5. WHEN configuration parameters change THEN it SHALL apply them without requiring code changes

### Requirement 6

**User Story:** As a user, I want the nicklee.tw ad replacer to have appropriate error handling and logging, so that I can troubleshoot issues and monitor the replacement process.

#### Acceptance Criteria

1. WHEN errors occur THEN it SHALL log them with descriptive messages
2. WHEN processing websites THEN it SHALL provide progress updates and status information
3. WHEN ads are found and replaced THEN it SHALL log the dimensions and positions
4. WHEN screenshots are taken THEN it SHALL confirm successful saves with file paths
5. WHEN the process completes THEN it SHALL provide a summary of total replacements and screenshots