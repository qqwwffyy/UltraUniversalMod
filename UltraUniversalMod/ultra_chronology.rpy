# Ultra Chronology: rollbackable choice history, with read-only AST inspection.
#
# Only public callback lists are extended. The AST is inspected to associate a
# menu with its branch; Ren'Py's menu implementation and choice screens are not
# replaced. A missing or unfamiliar AST simply leaves a choice unrecorded.

default ultra_chronology_events = []
default ultra_chronology_sequence = 0
default ultra_chronology_pending = None
default ultra_chronology_selected = None
default ultra_chronology_choices_page = 0
default ultra_chronology_scroll = ui.adjustment()
default persistent.ultra_chronology_recovery_slot = None
default persistent.ultra_chronology_seen_options = {}

init -3 python:
    import json as _ultra_chronology_json
    import hashlib as _ultra_chronology_hashlib
    import uuid as _ultra_chronology_uuid
    import os as _ultra_chronology_os

    class UltraChronology(object):
        """Per-save choice history. All gameplay data follows Ren'Py rollback."""

        _source_context_cache = {}
        _preview_ui_cache = {}
        _clean_screenshot = None
        _skip_next_checkpoint_screenshot = False
        _recovering = False

        @classmethod
        def events(cls):
            rows = getattr(store, "ultra_chronology_events", None)
            if not isinstance(rows, (list, tuple)):
                return []
            return [row for row in rows
                    if isinstance(row, dict) and row.get("kind") == "choice"]

        @classmethod
        def _in_game(cls):
            try:
                return (len(renpy.game.contexts) == 1 and
                        not getattr(store, "main_menu", False) and
                        hasattr(store, "ultra_chronology_events"))
            except Exception:
                return False

        @classmethod
        def _append(cls, event):
            rows = list(cls.events())
            sequence = getattr(store, "ultra_chronology_sequence", 0)
            if not isinstance(sequence, int) or isinstance(sequence, bool):
                sequence = 0
            sequence += 1
            event["seq"] = sequence
            rows.append(event)
            store.ultra_chronology_sequence = sequence
            store.ultra_chronology_events = rows
            return sequence

        @classmethod
        def _replace(cls, seq, changes):
            rows = list(cls.events())
            for position in range(len(rows) - 1, -1, -1):
                event = rows[position]
                if isinstance(event, dict) and event.get("seq") == seq:
                    updated = dict(event)
                    updated.update(changes)
                    rows[position] = updated
                    store.ultra_chronology_events = rows
                    return

        @classmethod
        def take_checkpoint_screenshot(cls):
            # A hidden screen remains in the last rendered framebuffer. Reuse
            # the frame captured before opening Ultra; never capture Ultra UI.
            if renpy.get_screen("ultra_main_menu") is not None:
                if cls._clean_screenshot is None:
                    return False
                renpy.game.interface.screenshot = cls._clean_screenshot
                return True
            renpy.take_screenshot()
            return renpy.game.interface.screenshot is not None

        @classmethod
        def remember_clean_screenshot(cls):
            cls._clean_screenshot = getattr(renpy.game.interface, "screenshot", None)

        @classmethod
        def forget_clean_screenshot(cls):
            cls._clean_screenshot = None

        @classmethod
        def _current_ast(cls):
            try:
                current = renpy.game.context().current
                return renpy.game.script.namemap.get(current)
            except Exception:
                return None

        @classmethod
        def menu_identity(cls, node):
            name = getattr(node, "name", None)
            if isinstance(name, str) and name:
                return name
            filename = getattr(node, "filename", None)
            linenumber = getattr(node, "linenumber", None)
            if filename is not None and linenumber is not None:
                return "{}:{}".format(filename, linenumber)
            return None

        @classmethod
        def _menu(cls, node):
            if node is None or not isinstance(node, renpy.ast.Menu):
                return
            options = []
            targets = []
            prompt = ""
            for label, condition, block in node.items:
                if not block:
                    if not prompt and isinstance(label, str):
                        prompt = label
                    continue
                if not isinstance(label, str):
                    continue
                # Interpolating every AST option would evaluate even hidden
                # branches, which may have side effects in arbitrary games.
                options.append({"text": label[:1000],
                                "conditional": str(condition or "True") != "True"})
                # Ordinary Ren'Py AST nodes have generated tuple names.
                # statement_callback resolves the current node through
                # menu_identity(), which falls back to filename:line for
                # those nodes. Normalize branch targets the same way so the
                # selected branch can be matched reliably.
                targets.append(cls.menu_identity(block[0]))
            if not options:
                return
            menu_name = cls.menu_identity(node)
            if menu_name is None:
                return
            rows = cls.events()
            if rows and isinstance(rows[-1], dict):
                last = rows[-1]
                if (last.get("kind") == "choice" and
                        last.get("menu_name") == menu_name and
                        last.get("chosen_index") is None):
                    store.ultra_chronology_pending = {
                        "seq": last.get("seq"), "menu_name": menu_name,
                        "targets": targets}
                    return
            seq = cls._append({"kind": "choice", "prompt": prompt[:1000],
                               "options": options, "chosen_index": None,
                               "menu_name": menu_name,
                               "context": cls.recent_dialogue(),
                               "checkpoint": None})
            store.ultra_chronology_pending = {
                "seq": seq, "menu_name": menu_name, "targets": targets}

        @classmethod
        def statement_callback(cls, statement_name):
            if not cls._in_game():
                return
            node = cls._current_ast()
            current_name = cls.menu_identity(node)
            pending = getattr(store, "ultra_chronology_pending", None)
            if (isinstance(pending, dict) and current_name is not None and
                    current_name != pending.get("menu_name")):
                targets = pending.get("targets", ())
                if isinstance(targets, (list, tuple)) and current_name in targets:
                    cls._replace(pending.get("seq"),
                                 {"chosen_index": targets.index(current_name)})
                    chosen_event = cls.event(pending.get("seq"))
                    cls.remember_choice(chosen_event)
                store.ultra_chronology_pending = None
            if statement_name.startswith("menu"):
                cls._menu(node)

        @classmethod
        def checkpoint_interaction(cls):
            """Save once when a real menu starts its interaction.

            A save resumes at the beginning of the menu statement. An
            interaction callback also avoids saving conditional menus that
            have no visible choices and therefore never interact.
            """
            if not cls._in_game() or not getattr(config, "save", True):
                return
            node = cls._current_ast()
            pending = getattr(store, "ultra_chronology_pending", None)
            if (not isinstance(node, renpy.ast.Menu) or
                    not isinstance(pending, dict) or
                    cls.menu_identity(node) != pending.get("menu_name")):
                return
            event = cls.event(pending.get("seq"))
            if not isinstance(event, dict) or event.get("kind") != "choice":
                return
            old_slot = event.get("checkpoint")
            if isinstance(old_slot, str) and cls.checkpoint_available(event):
                return
            slot = "ultra-chrono-" + _ultra_chronology_uuid.uuid4().hex
            cls._replace(event["seq"], {"checkpoint": slot})
            try:
                if cls._skip_next_checkpoint_screenshot:
                    screenshot_ready = False
                    cls._skip_next_checkpoint_screenshot = False
                else:
                    try:
                        screenshot_ready = cls.take_checkpoint_screenshot()
                    except Exception:
                        screenshot_ready = False
                renpy.save(slot, extra_info="Ultra Chronology: choice",
                           extra_json={"ultra_chronology_checkpoint": slot},
                           include_screenshot=screenshot_ready)
            except TypeError:
                # Older Ren'Py releases may lack extra_json.
                try:
                    renpy.save(slot, extra_info="Ultra Chronology: choice",
                               include_screenshot=screenshot_ready)
                except Exception:
                    cls._replace(event["seq"], {"checkpoint": None})
            except Exception:
                cls._replace(event["seq"], {"checkpoint": None})

        @classmethod
        def after_load(cls):
            cls.forget_clean_screenshot()
            if cls._recovering:
                cls._recovering = False
                persistent.ultra_chronology_recovery_slot = None
                renpy.save_persistent()
            store.ultra_chronology_selected = None
            rows = getattr(store, "ultra_chronology_events", None)
            if isinstance(rows, (list, tuple)):
                store.ultra_chronology_events = [
                    row for row in rows
                    if isinstance(row, dict) and row.get("kind") == "choice"]
            pending = getattr(store, "ultra_chronology_pending", None)
            if isinstance(pending, dict):
                if not any(isinstance(e, dict) and e.get("seq") == pending.get("seq")
                           for e in cls.events()):
                    store.ultra_chronology_pending = None
            cls.remember_choices(cls.events())

        @classmethod
        def event(cls, identifier):
            if identifier is None:
                return None
            for row in cls.events():
                if isinstance(row, dict) and row.get("seq") == identifier:
                    return row
            return None

        @classmethod
        def selection_key(cls, event):
            if not isinstance(event, dict):
                return None
            return event.get("seq")

        @classmethod
        def page_index(cls, value, count):
            try:
                value = int(value)
            except (TypeError, ValueError, OverflowError):
                value = 0
            return min(max(0, value), max(0, count - 1))

        @classmethod
        def option_text(cls, option):
            if isinstance(option, dict):
                return str(option.get("text") or "")
            return str(option) if option is not None else ""

        @classmethod
        def display_text(cls, value):
            """Use the active game's string translations for saved AST text."""
            raw = str(value or "")
            try:
                return renpy.translate_string(raw)
            except Exception:
                return raw

        @classmethod
        def recent_dialogue(cls):
            """Capture the translated line actually shown before this menu."""
            try:
                history = getattr(store, "_history_list", ())
                if not history:
                    return None
                entry = history[-1]
                raw = str(getattr(entry, "what", "") or "")
                if not raw:
                    return None
                try:
                    line = renpy.substitute(raw)
                except Exception:
                    line = raw
                return {"who": str(getattr(entry, "who", "") or "")[:120],
                        "text": str(line)[:1500]}
            except Exception:
                return None

        @classmethod
        def source_context(cls, event):
            """Best-effort context for choices recorded before this feature."""
            key = event.get("menu_name") if isinstance(event, dict) else None
            language = renpy.game.preferences.language
            cache_key = (str(key), language)
            if cache_key in cls._source_context_cache:
                return cls._source_context_cache[cache_key]
            result = None
            try:
                filename, line_text = str(key).rsplit(":", 1)
                menu_line = int(line_text)
                filename = _ultra_chronology_os.path.normcase(_ultra_chronology_os.path.normpath(filename))
                translator = renpy.game.script.translator
                closest = None
                closest_line = -1
                for original in translator.default_translates.values():
                    source = _ultra_chronology_os.path.normcase(_ultra_chronology_os.path.normpath(original.filename))
                    if source != filename:
                        continue
                    nodes = [original] if isinstance(original, renpy.ast.Say) else getattr(original, "block", ())
                    for say in nodes:
                        line = getattr(say, "linenumber", -1)
                        if isinstance(say, renpy.ast.Say) and closest_line < line < menu_line:
                            closest, closest_line = original, line
                if closest is not None and menu_line - closest_line <= 8:
                    translated = translator.language_translates.get((closest.identifier, language), closest)
                    lines = [translated] if isinstance(translated, renpy.ast.Say) else getattr(translated, "block", ())
                    lines = [n for n in lines if isinstance(n, renpy.ast.Say)]
                    if lines:
                        result = {"who": "", "text": str(lines[-1].what)[:1500]}
            except Exception:
                pass
            cls._source_context_cache[cache_key] = result
            return result

        @classmethod
        def context(cls, event):
            saved = event.get("context") if isinstance(event, dict) else None
            if isinstance(saved, dict) and saved.get("text"):
                return saved
            return cls.source_context(event)

        @classmethod
        def set_page(cls, page):
            store.ultra_chronology_choices_page = page
            store.ultra_chronology_scroll.change(0)

        @classmethod
        def choice_text(cls, event):
            options = event.get("options", ()) if isinstance(event, dict) else ()
            chosen = event.get("chosen_index") if isinstance(event, dict) else None
            if (isinstance(options, (list, tuple)) and isinstance(chosen, int) and
                    not isinstance(chosen, bool) and 0 <= chosen < len(options)):
                return cls.option_text(options[chosen])
            return None

        @classmethod
        def option_key(cls, event, index):
            if not isinstance(event, dict):
                return None
            menu_name = event.get("menu_name")
            options = event.get("options")
            if (menu_name is None or not isinstance(options, (list, tuple)) or
                    not isinstance(index, int) or isinstance(index, bool) or
                    not 0 <= index < len(options)):
                return None
            value = _ultra_chronology_json.dumps(
                [str(menu_name), index, cls.option_text(options[index])],
                ensure_ascii=False, separators=(",", ":"))
            return _ultra_chronology_hashlib.sha256(value.encode("utf-8")).hexdigest()

        @classmethod
        def remember_choices(cls, events):
            old = getattr(persistent, "ultra_chronology_seen_options", None)
            known = dict(old) if isinstance(old, dict) else {}
            changed = False
            for event in events:
                if not isinstance(event, dict) or event.get("kind") != "choice":
                    continue
                key = cls.option_key(event, event.get("chosen_index"))
                if key is not None and key not in known:
                    known[key] = True
                    changed = True
            if changed:
                try:
                    persistent.ultra_chronology_seen_options = known
                    renpy.save_persistent()
                except Exception:
                    pass

        @classmethod
        def remember_choice(cls, event):
            cls.remember_choices((event,))

        @classmethod
        def option_unseen(cls, event, index):
            if isinstance(event, dict) and event.get("chosen_index") == index:
                return False
            key = cls.option_key(event, index)
            if key is None:
                return False
            known = getattr(persistent, "ultra_chronology_seen_options", None)
            return not (isinstance(known, dict) and key in known)

        @classmethod
        def unseen_keys(cls, events):
            result = set()
            for event in events:
                if not isinstance(event, dict) or event.get("kind") != "choice":
                    continue
                options = event.get("options", ())
                if not isinstance(options, (list, tuple)):
                    continue
                for index in range(len(options)):
                    if cls.option_unseen(event, index):
                        result.add(cls.option_key(event, index))
            return result

        @classmethod
        def unseen_count(cls, event):
            return len(cls.unseen_keys((event,)))

        @classmethod
        def checkpoint_available(cls, event):
            slot = event.get("checkpoint") if isinstance(event, dict) else None
            if not isinstance(slot, str) or not slot.startswith("ultra-chrono-"):
                return False
            try:
                if not renpy.can_load(slot):
                    return False
                metadata = renpy.slot_json(slot) or {}
                marker = metadata.get("ultra_chronology_checkpoint")
                return marker is None or marker == slot
            except Exception:
                return False

        @classmethod
        def can_visit(cls, event):
            return (isinstance(event, dict) and event.get("kind") == "choice" and
                    cls.checkpoint_available(event))

        @classmethod
        def preview(cls, event):
            slot = event.get("checkpoint") if isinstance(event, dict) else None
            if not isinstance(slot, str):
                return None
            try:
                image = renpy.slot_screenshot(slot)
                if image is None or cls.preview_contains_ultra(slot, image):
                    return None
                return image
            except Exception:
                return None

        @classmethod
        def preview_contains_ultra(cls, slot, image):
            """Hide old thumbnails that captured the Ultra sidebar itself."""
            if slot in cls._preview_ui_cache:
                return cls._preview_ui_cache[slot]
            detected = False
            try:
                surface = image.load()
                width, height = surface.get_size()
                samples = [surface.get_at((int(width * 0.02), int(height * y)))
                           for y in (0.02, 0.12, 0.21)]
                sidebar = ((48, 42, 35), (48, 42, 35), (115, 85, 56))
                detected = all(all(abs(pixel[i] - expected[i]) <= 4 for i in range(3))
                               for pixel, expected in zip(samples, sidebar))
            except Exception:
                pass
            cls._preview_ui_cache[slot] = detected
            return detected

        @classmethod
        def visit(cls, event):
            """Preserve the present route, then load the exact pre-choice save."""
            if not cls.can_visit(event):
                renpy.notify(ultra_ui_t('chronology.the_checkpoint_for_this_choice_is_unavailable'))
                return
            in_game = cls._in_game()
            if not in_game and not getattr(store, "main_menu", False):
                renpy.notify(ultra_ui_t('chronology.you_can_jump_there_from_the_game_or'))
                return
            if in_game and not cls.recovery_available():
                recovery = "ultra-chrono-recovery"
                try:
                    try:
                        screenshot_ready = cls.take_checkpoint_screenshot()
                    except Exception:
                        screenshot_ready = False
                    renpy.save(recovery, extra_info="Ultra Chronology: return point",
                               include_screenshot=screenshot_ready)
                except Exception:
                    renpy.notify(ultra_ui_t('chronology.could_not_save_the_return_point_jump_cancelled'))
                    return
                try:
                    persistent.ultra_chronology_recovery_slot = recovery
                    renpy.save_persistent()
                except Exception:
                    renpy.notify(ultra_ui_t('chronology.could_not_remember_the_return_point_jump_cancelled'))
                    return
            renpy.hide_screen("ultra_main_menu")
            try:
                cls._skip_next_checkpoint_screenshot = True
                renpy.load(event["checkpoint"])
            except Exception:
                cls._skip_next_checkpoint_screenshot = False
                renpy.notify(ultra_ui_t('chronology.could_not_load_the_checkpoint'))
            else:
                cls._skip_next_checkpoint_screenshot = False
                renpy.notify(ultra_ui_t('chronology.could_not_load_the_checkpoint'))

        @classmethod
        def recovery_available(cls):
            slot = getattr(persistent, "ultra_chronology_recovery_slot", None)
            try:
                return isinstance(slot, str) and renpy.can_load(slot)
            except Exception:
                return False

        @classmethod
        def recover(cls):
            if not cls.recovery_available():
                renpy.notify(ultra_ui_t('chronology.the_return_point_is_no_longer_available'))
                return
            slot = persistent.ultra_chronology_recovery_slot
            cls._recovering = True
            try:
                renpy.load(slot)
            except Exception:
                cls._recovering = False
                renpy.notify(ultra_ui_t('chronology.could_not_load_the_return_point'))
            else:
                cls._recovering = False
                renpy.notify(ultra_ui_t('chronology.could_not_load_the_return_point'))

    if UltraChronology.statement_callback not in config.statement_callbacks:
        config.statement_callbacks.append(UltraChronology.statement_callback)
    if UltraChronology.checkpoint_interaction not in config.start_interact_callbacks:
        config.start_interact_callbacks.append(UltraChronology.checkpoint_interaction)
    if UltraChronology.after_load not in config.after_load_callbacks:
        config.after_load_callbacks.append(UltraChronology.after_load)

define ULTRA_CHRONO_CARD = "#25211C"
define ULTRA_CHRONO_BAR = "#302A23"
define ULTRA_CHRONO_ACCENT = "#C49A70"

style ultra_chrono_heading is ultra_page_title:
    color "#EEE4D7"

style ultra_chrono_title is ultra_card_title:
    color "#EEE4D7"

style ultra_chrono_text is ultra_description:
    color "#C1B3A2"

style ultra_chrono_button is ultra_small_button:
    background Solid(ULTRA_CHRONO_BAR)
    hover_background Solid("#40372D")
    selected_background Solid("#735538")

style ultra_chrono_button_text is ultra_small_button_text:
    color "#E4DACE"
    size ultra_scale_px(17)

style ultra_chrono_option is button:
    background Solid(ULTRA_CHRONO_CARD)
    hover_background Solid("#40372D")
    insensitive_background Solid(ULTRA_CHRONO_CARD)
    padding (ultra_scale_px(12), ultra_scale_px(9))
    yminimum ultra_scale_px(43)

style ultra_chrono_meta is ultra_description:
    size ultra_scale_px(15)
    color "#AA9886"

style ultra_chrono_recover is button:
    background Solid("#735538")
    hover_background Solid("#866746")
    padding (ultra_scale_px(18), ultra_scale_px(12))
    yminimum ultra_scale_px(52)

style ultra_chrono_recover_text is ultra_button_text:
    color "#EEE4D7"
    size ultra_scale_px(18)

style ultra_chrono_card_button is button:
    background Solid(ULTRA_CHRONO_BAR)
    hover_background Solid("#40372D")
    xfill True
    yminimum ultra_scale_px(44)
    padding (ultra_scale_px(12), ultra_scale_px(8))

style ultra_chrono_card_button_text is ultra_button_text:
    size ultra_scale_px(17)
    xalign 0.5
    xfill True

screen ultra_chronology_card(event, card_width, ordinal):
    $ _can_visit = UltraChronology.can_visit(event)
    $ _preview = UltraChronology.preview(event) if _can_visit else None
    $ _chosen = UltraChronology.display_text(UltraChronology.choice_text(event))
    $ _new = UltraChronology.unseen_count(event)
    $ _border = max(2, ultra_scale_px(2))
    $ _inner_width = card_width - 2 * _border
    $ _preview_height = int(_inner_width * 0.56)
    frame:
        xsize card_width
        background Solid(ULTRA_CHRONO_ACCENT if _new else ULTRA_CHRONO_CARD)
        padding (_border, _border)
        vbox:
            xfill True
            fixed:
                xsize _inner_width
                ysize _preview_height
                if _preview is not None:
                    add Transform(_preview, xysize=(_inner_width, _preview_height), fit="cover")
                else:
                    frame:
                        xsize _inner_width
                        ysize _preview_height
                        background Solid(ULTRA_CHRONO_BAR)
                        text ultra_ui_t('chronology.preview_unavailable') style "ultra_chrono_text" xalign 0.5 yalign 0.5 substitute False
            frame:
                xfill True
                yminimum ultra_scale_px(82)
                background Solid(ULTRA_CHRONO_CARD)
                padding (ultra_scale_px(14), ultra_scale_px(12))
                vbox:
                    spacing ultra_scale_px(7)
                    hbox:
                        text ultra_ui_t('chronology.choice_02d').format(ordinal) style "ultra_chrono_meta" substitute False
                    text (_chosen or ultra_ui_t('chronology.no_choice_made_yet')) substitute False style "ultra_chrono_title" xfill True
            textbutton ultra_ui_t('chronology.all_options_button') style "ultra_chrono_card_button" action Show("ultra_chronology_choice_modal", event=event, close_action=Hide("ultra_chronology_choice_modal")) substitute False

screen ultra_chronology_view():
    $ _choices = UltraChronology.events()
    $ _content_width = config.screen_width - ultra_scale_px(304)
    $ _gap = ultra_scale_px(18)
    $ _columns = max(1, min(5, (_content_width + _gap) // (ultra_scale_px(255) + _gap)))
    $ _page_size = 25
    $ _choice_pages = max(1, (len(_choices) + _page_size - 1) // _page_size)
    $ _choice_page = UltraChronology.page_index(store.ultra_chronology_choices_page, _choice_pages)
    $ _visible_choices = _choices[_choice_page * _page_size:(_choice_page + 1) * _page_size]
    $ _card_width = (_content_width - (_columns - 1) * _gap) // _columns
    vbox:
        xfill True
        yfill True
        spacing ultra_scale_px(16)
        hbox:
            xfill True
            vbox:
                text ultra_ui_t('nav.timeline') style "ultra_chrono_heading" substitute False
                text ultra_ui_t('chronology.choice_history_and_unseen_options') style "ultra_chrono_text" substitute False
            null xfill True
            text ultra_ui_t('chronology.unseen_options').format(len(UltraChronology.unseen_keys(_choices))) style "ultra_chrono_text" yalign 0.5 substitute False
        add Solid("#40372D", xysize=(_content_width, 1))
        if UltraChronology.recovery_available():
            frame:
                xfill True
                background Solid("#3D3025")
                padding (ultra_scale_px(16), ultra_scale_px(10))
                if _content_width >= ultra_scale_px(850):
                    hbox:
                        xfill True
                        vbox:
                            spacing ultra_scale_px(4)
                            text ultra_ui_t('chronology.return_point') style "ultra_chrono_title" color ULTRA_CHRONO_ACCENT substitute False
                            text ultra_ui_t('chronology.go_back_to_where_you_left_your_playthrough') style "ultra_chrono_meta" substitute False
                        null xfill True
                        textbutton ultra_ui_t('chronology.return_to_where_i_left_off') style "ultra_chrono_recover" action Function(UltraChronology.recover) yalign 0.5 substitute False
                else:
                    vbox:
                        xfill True
                        spacing ultra_scale_px(7)
                        text ultra_ui_t('chronology.return_point') style "ultra_chrono_title" color ULTRA_CHRONO_ACCENT substitute False
                        text ultra_ui_t('chronology.go_back_to_where_you_left_your_playthrough') style "ultra_chrono_meta" substitute False
                        textbutton ultra_ui_t('chronology.return_to_where_i_left_off') style "ultra_chrono_recover" action Function(UltraChronology.recover) substitute False
        if len(_choices) > _page_size:
            hbox:
                spacing ultra_scale_px(6)
                textbutton ultra_ui_t('chronology.earlier') style "ultra_chrono_button" sensitive (_choice_page > 0) action Function(UltraChronology.set_page, _choice_page - 1) substitute False
                text ultra_ui_t('common.page_count').format(_choice_page + 1, _choice_pages) style "ultra_chrono_text" yalign 0.5 substitute False
                textbutton ultra_ui_t('chronology.later') style "ultra_chrono_button" sensitive (_choice_page + 1 < _choice_pages) action Function(UltraChronology.set_page, _choice_page + 1) substitute False
        viewport:
            xfill True
            yfill True
            yadjustment store.ultra_chronology_scroll
            mousewheel True
            draggable True
            pagekeys True
            scrollbars None
            vbox:
                xfill True
                spacing _gap
                if _visible_choices:
                    for _row_start in range(0, len(_visible_choices), _columns):
                        hbox:
                            spacing _gap
                            for _column, _event in enumerate(_visible_choices[_row_start:_row_start + _columns]):
                                use ultra_chronology_card(_event, _card_width, _choice_page * _page_size + _row_start + _column + 1)
                else:
                    text ultra_ui_t('chronology.choices_will_appear_here_as_you_play') style "ultra_chrono_text" substitute False
screen ultra_chronology_choice_modal(event, close_action):
    modal True
    zorder 300
    key "K_ESCAPE" action close_action
    $ _options = event.get("options", ())
    $ _options = _options if isinstance(_options, (list, tuple)) else ()
    $ _can_visit = UltraChronology.can_visit(event)
    $ _preview = UltraChronology.preview(event) if _can_visit else None
    $ _dialog_width = min(ultra_scale_px(1040), config.screen_width - ultra_scale_px(64))
    $ _dialog_height = min(ultra_scale_px(700), config.screen_height - ultra_scale_px(64))
    $ _inner_width = _dialog_width - ultra_scale_px(44)
    $ _wide = _dialog_width >= ultra_scale_px(820)
    $ _body_height = _dialog_height - ultra_scale_px(132)
    $ _image_width = int(_inner_width * 0.47) if _wide else _inner_width
    $ _image_height = min(int(_image_width * 0.5625), int(_body_height * 0.52)) if _wide else min(ultra_scale_px(190), int(_body_height * 0.34))
    $ _prompt = UltraChronology.display_text(event.get("prompt"))
    $ _context = UltraChronology.context(event)
    button:
        xfill True
        yfill True
        background Solid("#000000BB")
        hover_background Solid("#000000BB")
        action NullAction()
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width
        ysize _dialog_height
        background Solid("#181512")
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(14)
            hbox:
                xfill True
                vbox:
                    spacing ultra_scale_px(4)
                    text ultra_ui_t('chronology.all_options_heading') style "ultra_chrono_heading" substitute False
                    text ultra_ui_t('chronology.review_your_choice_and_available_paths') style "ultra_chrono_meta" substitute False
                null xfill True
                textbutton ultra_ui_t('chronology.close') style "ultra_chrono_button" action close_action substitute False
            add Solid("#40372D", xysize=(_inner_width, 1))
            if _wide:
                hbox:
                    xfill True
                    ysize _body_height
                    spacing ultra_scale_px(20)
                    vbox:
                        xsize _image_width
                        ysize _body_height
                        spacing ultra_scale_px(14)
                        use ultra_chronology_modal_preview(_preview, _image_width, _image_height)
                        use ultra_chronology_dialogue(_context, _prompt, _image_width, _body_height - _image_height - ultra_scale_px(14))
                    use ultra_chronology_modal_variants(event, _options, _can_visit, close_action, _body_height)
            else:
                viewport:
                    xfill True
                    ysize _body_height
                    mousewheel True
                    draggable True
                    scrollbars None
                    vbox:
                        xfill True
                        spacing ultra_scale_px(12)
                        use ultra_chronology_modal_preview(_preview, _image_width, _image_height)
                        use ultra_chronology_dialogue(_context, _prompt, _image_width, ultra_scale_px(110))
                        use ultra_chronology_modal_variants(event, _options, _can_visit, close_action, max(ultra_scale_px(220), _body_height - _image_height - ultra_scale_px(134)))

screen ultra_chronology_modal_preview(preview, width, height):
    if preview is not None:
        add Transform(preview, xysize=(width, height), fit="contain")
    else:
        frame:
            xsize width
            ysize height
            background Solid(ULTRA_CHRONO_BAR)
            text ultra_ui_t('chronology.preview_unavailable') style "ultra_chrono_text" xalign 0.5 yalign 0.5 substitute False

screen ultra_chronology_dialogue(context, prompt, width, height):
    $ _text = str(context.get("text") or "") if isinstance(context, dict) else prompt
    $ _who = str(context.get("who") or "") if isinstance(context, dict) else ""
    frame:
        xsize width
        ysize height
        background Solid(ULTRA_CHRONO_CARD)
        padding (ultra_scale_px(14), ultra_scale_px(12))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(8)
            text ultra_ui_t('chronology.before_the_choice') style "ultra_chrono_meta" color ULTRA_CHRONO_ACCENT substitute False
            if _who:
                text _who substitute False style "ultra_chrono_meta" color "#EEE4D7"
            viewport:
                xfill True
                yfill True
                mousewheel True
                draggable True
                scrollbars None
                text (_text or ultra_ui_t('chronology.the_line_before_this_choice_was_not_saved')) substitute False style "ultra_chrono_text" xfill True

screen ultra_chronology_modal_variants(event, options, can_visit, close_action, height):
    vbox:
        xfill True
        ysize height
        spacing ultra_scale_px(10)
        text ultra_ui_t('chronology.choice_options') style "ultra_chrono_title" substitute False
        viewport:
            xfill True
            ysize max(ultra_scale_px(100), height - ultra_scale_px(108))
            mousewheel True
            draggable True
            pagekeys True
            scrollbars None
            vbox:
                xfill True
                spacing ultra_scale_px(7)
                for _index, _option in enumerate(options):
                    use ultra_chronology_variant(event, _option, _index, can_visit, close_action)
        frame:
            xfill True
            background Solid(ULTRA_CHRONO_BAR)
            padding (ultra_scale_px(12), ultra_scale_px(8))
            text (ultra_ui_t('chronology.another_option_will_reopen_the_choice_in_the') if can_visit else ultra_ui_t('chronology.checkpoint_unavailable_options_are_shown_for_reference')) style "ultra_chrono_meta" xfill True substitute False

screen ultra_chronology_variant(event, option, index, can_visit, close_action):
    $ _chosen = event.get("chosen_index") == index
    $ _new = UltraChronology.option_unseen(event, index)
    $ _label = UltraChronology.display_text(UltraChronology.option_text(option)) or ultra_ui_t('chronology.empty_option')
    $ _conditional = isinstance(option, dict) and option.get("conditional")
    $ _status = (ultra_ui_t('chronology.chosen') if _chosen else ultra_ui_t('chronology.new_path') if _new else ultra_ui_t('chronology.seen_before')) + (ultra_ui_t('chronology.conditional') if _conditional else "")
    if _chosen or not can_visit:
        frame:
            xfill True
            background Solid("#49392C" if _chosen else ULTRA_CHRONO_CARD)
            padding (ultra_scale_px(14), ultra_scale_px(11))
            use ultra_chronology_variant_content(_label, _status, _chosen, _new, False)
    else:
        button:
            style "ultra_chrono_option"
            xfill True
            action [close_action, Function(UltraChronology.visit, event)]
            use ultra_chronology_variant_content(_label, _status, _chosen, _new, True)

screen ultra_chronology_variant_content(label, status, chosen, new, actionable):
    vbox:
        xfill True
        spacing ultra_scale_px(5)
        hbox:
            xfill True
            text status substitute False style "ultra_chrono_meta" color (ULTRA_CHRONO_ACCENT if chosen or new else "#AA9886")
        text label substitute False style "ultra_chrono_text" color ("#EEE4D7" if chosen else "#E4DACE") xfill True


