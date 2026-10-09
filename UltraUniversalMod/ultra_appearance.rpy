# Game appearance only. Never change gui.*, style.default, or Ultra's styles.

default persistent.ultra_appearance_preset = "original"
default persistent.ultra_appearance_font = "original"
default persistent.ultra_appearance_size = "normal"

init 999 python:
    import builtins as _ultra_appearance_builtins

    class UltraAppearance(object):
        font_directory = "UltraUniversalMod/fonts/"
        presets = (("original", 'appearance.original'), ("soft_dialogue", 'appearance.soft_dialogue'))
        sizes = (("smaller", 'appearance.smaller'), ("normal", 'appearance.normal'), ("larger", 'appearance.larger'))
        size_factors = {"smaller": 0.90, "normal": 1.0, "larger": 1.12}

        # Concrete game screen styles. Avoid shared parents used by Ultra.
        game_text_styles = (
            "say_label", "say_dialogue", "say_thought",
            "nvl_label", "nvl_dialogue", "nvl_thought", "nvl_button_text",
            "choice_button_text", "quick_button_text", "navigation_button_text",
            "main_menu_text", "main_menu_title", "main_menu_version",
            "game_menu_label_text", "return_button_text", "about_label_text",
            "about_text", "page_label_text", "page_button_text",
            "slot_button_text", "slot_time_text", "slot_name_text",
            "pref_label_text", "radio_button_text", "check_button_text",
            "slider_button_text", "history_name_text", "history_text",
            "help_button_text", "help_label_text", "help_text",
            "confirm_prompt_text", "confirm_button_text", "skip_text",
            "skip_triangle", "notify_text", "bubble_who", "bubble_what",
            "input_prompt", "input",
        )

        def __init__(self):
            self._original = None
            paths = sorted(path for path in renpy.list_files()
                           if path.startswith(self.font_directory)
                           and path.lower().endswith((".ttf", ".otf"))
                           and "/" not in path[len(self.font_directory):])
            names = {
                "NotoSerif-Regular.ttf": "Noto Serif",
                "NotoSerif-Bold.ttf": 'appearance.noto_serif_bold',
                "DejaVuSans.ttf": "DejaVu Sans",
                "Comfortaa-Regular.ttf": "Comfortaa",
            }
            self.fonts = [(path, names.get(path.split("/")[-1],
                          path.split("/")[-1].rsplit(".", 1)[0].replace("_", " ").replace("-", " · ")))
                          for path in paths]

            width, height, fade = 3000, 480, 90
            pieces = []
            for y in range(fade):
                alpha = int((y / float(fade)) * 0.60 * 255)
                pieces.extend(((0, y), Solid("#0b0b0c{:02x}".format(alpha), xsize=width, ysize=1)))
            pieces.extend(((0, fade), Solid("#0b0b0c99", xsize=width, ysize=height - fade * 2)))
            for y in range(fade):
                alpha = int(((fade - y) / float(fade)) * 0.60 * 255)
                pieces.extend(((0, height - fade + y), Solid("#0b0b0c{:02x}".format(alpha), xsize=width, ysize=1)))
            background = Composite((width, height), *pieces)

            self.preset_values = {
                "window": {
                    "xalign": 0.5, "yalign": 1.0, "xfill": True,
                    "ysize": 480, "background": background,
                    "left_padding": 320, "right_padding": 320,
                    "top_padding": 130, "bottom_padding": 50,
                },
                "namebox": {
                    "xpos": 0.5, "xanchor": 0.5, "ypos": -15,
                    "background": None,
                },
                "say_label": {
                    "xalign": 0.5, "textalign": 0.5, "yalign": 0.5,
                    "size": 42, "color": "#FFF2CC", "kerning": 0.6,
                    "outlines": [(2.0, "#050505", 0, -3)],
                },
                "say_dialogue": {
                    "xalign": 0.5,
                    "ypos": 45, "textalign": 0.5, "size": 42,
                    "color": "#FFF2CC", "kerning": 0.6, "line_spacing": 18,
                    "outlines": [(2.0, "#050505", 0, -3)],
                    "adjust_spacing": False,
                },
            }

        def _target_styles(self):
            return set(self.preset_values) | set(self.game_text_styles)

        def _style(self, name):
            try:
                return style.get(name)
            except Exception:
                return None

        def _apply(self):
            # Style fields are not resolved yet when build_styles_callbacks run.
            # Keep the original declarations instead of reading fields like
            # xpos/ysize, which still contain engine defaults at this point.
            if self._original is None:
                dialogue = self._style("say_dialogue")
                window = self._style("window")
                if dialogue is None or window is None:
                    return
                # The first callback can run before game style declarations.
                # Wait for standard ADV styles without assuming a game's
                # particular positions, sizes, or background image.
                if not dialogue.properties or not window.properties:
                    return
                self._original = {}
                for name in self._target_styles():
                    game_style = self._style(name)
                    if game_style is None:
                        continue
                    self._original[name] = [_ultra_appearance_builtins.dict(properties)
                                            for properties in game_style.properties]

            for name, original_properties in self._original.items():
                game_style = self._style(name)
                if game_style is None:
                    continue
                game_style.properties[:] = [_ultra_appearance_builtins.dict(properties)
                                            for properties in original_properties]

            if self.preset == "soft_dialogue":
                for name, properties in self.preset_values.items():
                    game_style = self._style(name)
                    if game_style is not None:
                        for prop, value in properties.items():
                            setattr(game_style, prop, value)

            if self.font != "original":
                for name in self.game_text_styles:
                    game_style = self._style(name)
                    if game_style is not None:
                        game_style.font = self.font

            if self.size_mode != "normal":
                factor = self.size_factors[self.size_mode]
                dialogue_size = 42 if self.preset == "soft_dialogue" else gui.text_size
                name_size = 42 if self.preset == "soft_dialogue" else gui.name_text_size
                for name in ("say_dialogue", "say_thought", "nvl_dialogue", "nvl_thought"):
                    game_style = self._style(name)
                    if game_style is not None:
                        game_style.size = int(round(dialogue_size * factor))
                for name in ("say_label", "nvl_label"):
                    game_style = self._style(name)
                    if game_style is not None:
                        game_style.size = int(round(name_size * factor))

        @property
        def preset(self):
            value = persistent.ultra_appearance_preset
            return value if value in ("original", "soft_dialogue") else "original"

        @property
        def font(self):
            value = persistent.ultra_appearance_font
            return value if isinstance(value, str) and value in dict(self.fonts) else "original"

        @property
        def size_mode(self):
            value = persistent.ultra_appearance_size
            return value if isinstance(value, str) and value in self.size_factors else "normal"

        def _refresh(self):
            renpy.style.rebuild()
            renpy.save_persistent()
            renpy.restart_interaction()

        def set_preset(self, value):
            if value not in ("original", "soft_dialogue"):
                return
            if value == "original":
                self.reset()
                return
            persistent.ultra_appearance_preset = value
            if value == "soft_dialogue" and self.font == "original":
                preferred = self.font_directory + "NotoSerif-Bold.ttf"
                if preferred in dict(self.fonts):
                    persistent.ultra_appearance_font = preferred
            self._refresh()

        def set_font(self, value):
            if value != "original" and value not in dict(self.fonts):
                return
            persistent.ultra_appearance_font = value
            self._refresh()

        def set_size(self, value):
            if value not in self.size_factors:
                return
            persistent.ultra_appearance_size = value
            self._refresh()

        def reset(self):
            persistent.ultra_appearance_preset = "original"
            persistent.ultra_appearance_font = "original"
            persistent.ultra_appearance_size = "normal"
            self._refresh()

    ultra_appearance = UltraAppearance()
    if ultra_appearance._apply not in config.build_styles_callbacks:
        config.build_styles_callbacks.append(ultra_appearance._apply)
