import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Responsive layout breakpoints for Desktop, Tablet, and Mobile.
class MatteBreakpoints {
  MatteBreakpoints._();

  /// Width <= 768px renders Mobile layout; Width > 768px renders Desktop/Tablet layout.
  static const double mobileMaxWidth = 768.0;
  static const double tabletMaxWidth = 1100.0;
  static const double chatMaxWidth = 780.0;
  static const double sidebarExpandedWidth = 260.0;
  static const double sidebarCollapsedWidth = 0.0;

  static bool isMobile(BuildContext context) =>
      MediaQuery.sizeOf(context).width <= mobileMaxWidth;

  static bool isDesktopOrTablet(BuildContext context) =>
      MediaQuery.sizeOf(context).width > mobileMaxWidth;
}

/// Perceptually calibrated Solid Matte / Zinc design tokens from `app/config.py`.
/// Strictly zero gradients, zero glossy glassmorphism, zero glowing shadows.
class MatteColors {
  MatteColors._();

  // Surface Tokens
  static const Color canvas = Color(0xFF09090B); // Zinc 950 (Canvas background)
  static const Color panel = Color(0xFF18181B); // Zinc 900 (Solid cards & controls)
  static const Color panelHover = Color(0xFF27272A); // Zinc 800 (Interactive hover/active)
  static const Color inset = Color(0xFF121215); // Zinc 925 (Sunken inputs/search)

  // Border Tokens
  static const Color borderSubtle = Color(0xFF27272A); // Zinc 800 (1px hairline)
  static const Color borderStrong = Color(0xFF3F3F46); // Zinc 700 (Focus border)

  // Text Tokens
  static const Color textPrimary = Color(0xFFF4F4F5); // Zinc 100
  static const Color textSecondary = Color(0xFFA1A1AA); // Zinc 400
  static const Color textMuted = Color(0xFF71717A); // Zinc 500

  // Knowledge Graph Node Tokens (Zinc Baseline)
  static const Color nodePerson = Color(0xFF8B8CF8); // Slate Lavender
  static const Color nodeEmail = Color(0xFF4A9EBA); // Cerulean Gray
  static const Color nodeProject = Color(0xFF43A077); // Muted Emerald
  static const Color nodeTool = Color(0xFFC98A3E); // Muted Amber
  static const Color nodeTopic = Color(0xFFB8607A); // Steel Rose
  static const Color nodeDefault = Color(0xFF71717A); // Neutral Slate

  // Semantic Status Tokens (Matte calibrated)
  static const Color statusConnected = Color(0xFF43A077); // Muted Emerald
  static const Color statusWarning = Color(0xFFC98A3E); // Muted Amber
  static const Color statusDanger = Color(0xFFB8607A); // Steel Rose
  static const Color statusMuted = Color(0xFF71717A); // Zinc 500

  /// Palettes matching `DESIGN_TOKENS["palettes"]` in `app/config.py`.
  static const Map<String, Map<String, Color>> graphPalettes = {
    'zinc': {
      'Person': Color(0xFF8B8CF8),
      'Email': Color(0xFF4A9EBA),
      'Project': Color(0xFF43A077),
      'Tool': Color(0xFFC98A3E),
      'Topic': Color(0xFFB8607A),
      'Default': Color(0xFF71717A),
    },
    'stone': {
      'Person': Color(0xFFC87A5B),
      'Email': Color(0xFF6B8FA3),
      'Project': Color(0xFF769371),
      'Tool': Color(0xFFB8974A),
      'Topic': Color(0xFFA4778B),
      'Default': Color(0xFF78716C),
    },
    'basalt': {
      'Person': Color(0xFF7E74AD),
      'Email': Color(0xFF5285AA),
      'Project': Color(0xFF4E9177),
      'Tool': Color(0xFFBA8B4F),
      'Topic': Color(0xFFB05D5D),
      'Default': Color(0xFF64748B),
    },
  };

  /// Resolves the color for a given entity type and palette name.
  static Color colorForNodeType(String? type, {String palette = 'zinc'}) {
    final activePalette = graphPalettes[palette] ?? graphPalettes['zinc']!;
    if (type == null || type.isEmpty) {
      return activePalette['Default'] ?? nodeDefault;
    }
    // Match case-insensitively
    for (final entry in activePalette.entries) {
      if (entry.key.toLowerCase() == type.toLowerCase()) {
        return entry.value;
      }
    }
    return activePalette['Default'] ?? nodeDefault;
  }

  /// Parses a hex color string like `#8b8cf8` with fallback to `nodeDefault`.
  static Color fromHex(String? hexString, {Color fallback = nodeDefault}) {
    if (hexString == null || hexString.isEmpty) return fallback;
    final cleaned = hexString.replaceFirst('#', '').trim();
    if (cleaned.length == 6) {
      final parsed = int.tryParse('FF$cleaned', radix: 16);
      if (parsed != null) return Color(parsed);
    } else if (cleaned.length == 8) {
      final parsed = int.tryParse(cleaned, radix: 16);
      if (parsed != null) return Color(parsed);
    }
    return fallback;
  }
}

/// Solid Matte Theme configuration for Synapse.
class MatteTheme {
  MatteTheme._();

  static ThemeData get darkTheme {
    final interFontFamily = GoogleFonts.inter().fontFamily;
    final baseTextTheme = ThemeData.dark().textTheme.apply(
          fontFamily: interFontFamily,
          bodyColor: MatteColors.textPrimary,
          displayColor: MatteColors.textPrimary,
        );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      fontFamily: interFontFamily,
      scaffoldBackgroundColor: MatteColors.canvas,
      canvasColor: MatteColors.canvas,
      cardColor: MatteColors.panel,
      dividerColor: MatteColors.borderSubtle,
      splashColor: Colors.transparent,
      highlightColor: Colors.transparent,
      hoverColor: MatteColors.panelHover,
      colorScheme: const ColorScheme.dark(
        surface: MatteColors.panel,
        primary: MatteColors.textPrimary,
        secondary: MatteColors.textSecondary,
        error: MatteColors.statusDanger,
        onSurface: MatteColors.textPrimary,
        onPrimary: MatteColors.canvas,
        outline: MatteColors.borderSubtle,
      ),
      textTheme: baseTextTheme.copyWith(
        headlineMedium: baseTextTheme.headlineMedium?.copyWith(
          color: MatteColors.textPrimary,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
        ),
        titleLarge: baseTextTheme.titleLarge?.copyWith(
          color: MatteColors.textPrimary,
          fontWeight: FontWeight.w600,
          fontSize: 18,
          letterSpacing: -0.3,
        ),
        titleMedium: baseTextTheme.titleMedium?.copyWith(
          color: MatteColors.textPrimary,
          fontWeight: FontWeight.w500,
          fontSize: 15,
          letterSpacing: -0.2,
        ),
        bodyLarge: baseTextTheme.bodyLarge?.copyWith(
          color: MatteColors.textPrimary,
          fontSize: 14.5,
          height: 1.55,
        ),
        bodyMedium: baseTextTheme.bodyMedium?.copyWith(
          color: MatteColors.textPrimary,
          fontSize: 13.5,
          height: 1.5,
        ),
        bodySmall: baseTextTheme.bodySmall?.copyWith(
          color: MatteColors.textSecondary,
          fontSize: 12,
          height: 1.4,
        ),
        labelSmall: baseTextTheme.labelSmall?.copyWith(
          color: MatteColors.textMuted,
          fontSize: 11,
          letterSpacing: 0.2,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: MatteColors.canvas,
        foregroundColor: MatteColors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
      ),
      drawerTheme: const DrawerThemeData(
        backgroundColor: MatteColors.panel,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          side: BorderSide(color: MatteColors.borderSubtle, width: 1),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: MatteColors.panel,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: MatteColors.borderSubtle, width: 1),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: MatteColors.inset,
        isDense: true,
        hintStyle: const TextStyle(
          color: MatteColors.textMuted,
          fontSize: 13.5,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 11,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(
            color: MatteColors.borderSubtle,
            width: 1,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(
            color: MatteColors.borderStrong,
            width: 1,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(
            color: MatteColors.statusDanger,
            width: 1,
          ),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: const BorderSide(
            color: MatteColors.statusDanger,
            width: 1,
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: MatteColors.borderSubtle,
        thickness: 1,
        space: 1,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: MatteColors.panel,
        contentTextStyle: const TextStyle(
          color: MatteColors.textPrimary,
          fontSize: 13,
        ),
        elevation: 0,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: const BorderSide(color: MatteColors.borderStrong, width: 1),
        ),
      ),
    );
  }

  /// Helper decoration for solid matte panels (`#18181b` with `#27272a` 1px border).
  static BoxDecoration panelDecoration({
    Color color = MatteColors.panel,
    Color borderColor = MatteColors.borderSubtle,
    double borderRadius = 6.0,
  }) {
    return BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(color: borderColor, width: 1),
    );
  }

  /// Helper decoration for sunken inset fields (`#121215` with `#27272a` or `#3f3f46` 1px border).
  static BoxDecoration insetDecoration({
    bool isFocused = false,
    double borderRadius = 6.0,
  }) {
    return BoxDecoration(
      color: MatteColors.inset,
      borderRadius: BorderRadius.circular(borderRadius),
      border: Border.all(
        color: isFocused ? MatteColors.borderStrong : MatteColors.borderSubtle,
        width: 1,
      ),
    );
  }
}
