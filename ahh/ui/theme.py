"""
Design tokens for AHH! UI theme.
=================================
Clean minimalist palette with soft blue accent.
Import: from ahh.ui.theme import T
"""


class T:
    """Theme tokens — minimalist with #7BB8D4 accent."""

    # ── Surfaces ────────────────────────────────────────────────────
    WHITE          = "#FFFFFF"
    BG             = "#FAFAFA"
    BG_HOVER       = "#F5F5F5"
    BG_ACTIVE      = "#F0F0F0"
    BG_MUTED       = "#F7F7F7"

    # ── Borders (thin, subtle) ──────────────────────────────────────
    BORDER         = "#E5E5E5"
    BORDER_LIGHT   = "#EBEBEB"
    BORDER_FOCUS   = "#BDBDBD"

    # ── Text ────────────────────────────────────────────────────────
    TEXT_PRIMARY    = "#1A1A1A"
    TEXT_BODY       = "#333333"
    TEXT_SECONDARY  = "#666666"
    TEXT_MUTED      = "#999999"
    TEXT_HINT       = "#BBBBBB"
    TEXT_PLACEHOLDER = "#CCCCCC"
    TEXT_WHITE      = "#FFFFFF"

    # ── Accent (soft blue) ─────────────────────────────────────────
    ACCENT         = "#7BB8D4"
    ACCENT_HOVER   = "#69A6C2"
    ACCENT_PRESS   = "#5794B0"
    ACCENT_LIGHT   = "#D6EAF3"   # very light tint for backgrounds

    # ── Active state (soft blue tint) ──────────────────────────────
    ACTIVE_BG      = "#EDF5F9"
    ACTIVE_BORDER  = "#B8D8E8"

    # ── Completed state ─────────────────────────────────────────────
    CHECK_BG       = "#D6EAF3"
    CHECK_TEXT     = "#7BB8D4"

    # ── Typography ──────────────────────────────────────────────────
    FONT_FAMILY    = "DM Sans"
    FONT_HEADING   = "DM Serif Display"
    FONT_XS        = 10
    FONT_SM        = 11
    FONT_MD        = 12
    FONT_LG        = 13
    FONT_XL        = 14
    FONT_XXL       = 15
    FONT_ICON      = 16

    # ── Spacing (4px grid) ──────────────────────────────────────────
    SP_1           = 4
    SP_2           = 8
    SP_3           = 12
    SP_4           = 16
    SP_5           = 20
    SP_6           = 24
    SP_8           = 32
    SP_10          = 40

    # ── Radii ───────────────────────────────────────────────────────
    RADIUS_SM      = 8
    RADIUS_MD      = 12
    RADIUS_LG      = 16
    RADIUS_XL      = 20
    RADIUS_PILL    = 999

    # ── Shadows ─────────────────────────────────────────────────────
    SHADOW_MARGIN  = 10

    # ── Animation Durations (ms) ────────────────────────────────────
    ANIM_FAST      = 120
    ANIM_NORMAL    = 200
    ANIM_SLOW      = 400

    # ── QSS Generators ──────────────────────────────────────────────
    @staticmethod
    def btn_pill(
        bg: str = BG,
        fg: str = TEXT_BODY,
        border: str = BORDER,
        hover_bg: str = BG_HOVER,
        hover_border: str = BORDER_FOCUS,
        press_bg: str = BG_ACTIVE,
        press_border: str = BORDER_FOCUS,
        press_fg: str = TEXT_PRIMARY,
        min_h: int = 40,
        font_pt: int = 12,
    ) -> str:
        return f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 0.5px solid {border};
                border-radius: 999px;
                padding: 8px 18px;
                min-height: {min_h}px;
                font-family: DM Sans;
                font-size: {font_pt}pt;
            }}
            QPushButton:hover {{
                background: {hover_bg};
                border-color: {hover_border};
            }}
            QPushButton:pressed {{
                background: {press_bg};
                border-color: {press_border};
                color: {press_fg};
            }}
        """

    @staticmethod
    def btn_accent(
        bg: str = ACCENT,
        fg: str = TEXT_WHITE,
        hover_bg: str = ACCENT_HOVER,
        press_bg: str = ACCENT_PRESS,
        min_h: int = 40,
        font_pt: int = 12,
    ) -> str:
        return f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: none;
                border-radius: 999px;
                padding: 8px 22px;
                min-height: {min_h}px;
                font-family: DM Sans;
                font-size: {font_pt}pt;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {hover_bg};
            }}
            QPushButton:pressed {{
                background: {press_bg};
            }}
        """

    @staticmethod
    def input_pill(
        bg: str = WHITE,
        fg: str = TEXT_PRIMARY,
        border: str = BORDER,
        focus_border: str = ACCENT,
        focus_bg: str = WHITE,
        placeholder: str = TEXT_PLACEHOLDER,
        min_h: int = 40,
        font_pt: int = 12,
    ) -> str:
        return f"""
            QLineEdit {{
                background: {bg};
                color: {fg};
                border: 0.5px solid {border};
                border-radius: 999px;
                padding: 8px 18px;
                min-height: {min_h}px;
                font-family: DM Sans;
                font-size: {font_pt}pt;
                selection-background-color: #D6EAF3;
            }}
            QLineEdit:focus {{
                border: 1px solid {focus_border};
                background: {focus_bg};
                padding: 7px 17px;
            }}
            QLineEdit::placeholder {{
                color: {placeholder};
            }}
        """
