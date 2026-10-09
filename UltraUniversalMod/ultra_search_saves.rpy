# Variable/label search and Ren'Py save-slot browser.

default ultra_search_query = ""
default ultra_search_results = []
default ultra_search_page = 1
default ultra_search_last_query = None
default ultra_search_last_options = None
default ultra_search_has_run = False
default ultra_search_frozen = {}
default ultra_save_selected_page = 1

init 800 python:
    import ast as _ultra_search_ast
    import copy as _ultra_search_copy
    import re as _ultra_search_re
    import time as _ultra_save_time
    import types as _ultra_search_types

    class UltraSearchService(object):
        page_size = 20

        @staticmethod
        def options_signature():
            return (persistent.ultra_search_type, persistent.ultra_search_recursive,
                    persistent.ultra_search_persistent, persistent.ultra_search_objects,
                    persistent.ultra_search_internal, persistent.ultra_search_wildcards,
                    persistent.ultra_search_unsupported)

        @staticmethod
        def is_runtime_symbol(value):
            return isinstance(value, (_ultra_search_types.ModuleType,
                                      _ultra_search_types.FunctionType,
                                      _ultra_search_types.BuiltinFunctionType,
                                      _ultra_search_types.MethodType, type))

        @staticmethod
        def is_supported_value(value):
            return isinstance(value, (type(None), str, bool, int, float, dict, list, tuple, set))

        @staticmethod
        def display_value(value, limit=88):
            if isinstance(value, (type(None), bool, int, float, str)):
                shown = repr(value)
            elif isinstance(value, (list, tuple, dict, set)):
                shown = ultra_t('saves.items').format(type(value).__name__, len(value))
            else:
                shown = "<{}>".format(type(value).__name__)
            return shown if len(shown) <= limit else shown[:max(1, limit - 1)] + "…"

        @classmethod
        def match(cls, text, query):
            text, query = str(text), str(query)
            if persistent.ultra_search_wildcards:
                pattern = _ultra_search_re.escape(query).replace(r"\*", ".*").replace(r"\?", ".")
                try:
                    return bool(_ultra_search_re.search(pattern, text, _ultra_search_re.I))
                except Exception:
                    return False
            return query.casefold() in text.casefold()

        @classmethod
        def children(cls, value):
            if isinstance(value, dict):
                return iter(value.items())
            if isinstance(value, (list, tuple)):
                return enumerate(value)
            try:
                attributes = vars(value)
                return ((key, item) for key, item in attributes.items()
                        if isinstance(key, str) and not key.startswith("__"))
            except Exception:
                return iter(())

        @classmethod
        def row(cls, name, value, segments):
            return {"name": name, "value": value, "segments": list(segments), "type": type(value).__name__}

        @classmethod
        def walk(cls, name, value, segments, query, mode, rows, visited, depth=0):
            if len(rows) >= 5000 or depth > 5 or cls.is_runtime_symbol(value):
                return
            supported = cls.is_supported_value(value)
            if mode == "variable names" and (supported or persistent.ultra_search_unsupported) and cls.match(name, query):
                rows.append(cls.row(name, value, segments))
            elif mode == "values":
                try:
                    if isinstance(value, str) and cls.match(value, query):
                        rows.append(cls.row(name, value, segments))
                    elif isinstance(value, bool) and query.strip().casefold() in ("true", "false") and value == (query.strip().casefold() == "true"):
                        rows.append(cls.row(name, value, segments))
                    elif isinstance(value, int) and not isinstance(value, bool) and str(value) == query.strip():
                        rows.append(cls.row(name, value, segments))
                    elif isinstance(value, float) and str(value) == query.strip():
                        rows.append(cls.row(name, value, segments))
                    elif value is None and query.strip().casefold() == "none":
                        rows.append(cls.row(name, value, segments))
                    elif persistent.ultra_search_unsupported and not supported and cls.match(cls.display_value(value, 256), query):
                        rows.append(cls.row(name, value, segments))
                except Exception:
                    pass
            if len(rows) >= 5000 or not persistent.ultra_search_objects or depth >= 5:
                return
            if isinstance(value, (dict, list, tuple)) or hasattr(value, "__dict__"):
                identity = id(value)
                if identity in visited:
                    return
                visited.add(identity)
            for key, item in cls.children(value):
                if len(rows) >= 5000:
                    break
                if isinstance(key, str) and key.startswith("_") and not persistent.ultra_search_internal:
                    continue
                try:
                    child_name = "{}[{}]".format(name, repr(key)) if isinstance(value, (dict, list, tuple)) else "{}.{}".format(name, key)
                    cls.walk(child_name, item, segments + [key], query, mode, rows, visited, depth + 1)
                except Exception:
                    continue

        @classmethod
        def search(cls, query):
            query = str(query or "")
            mode = persistent.ultra_search_type
            if mode == "labels":
                try:
                    labels = renpy.get_all_labels()
                except Exception:
                    labels = []
                if persistent.ultra_search_recursive and ultra_search_has_run:
                    labels = [row["name"] for row in ultra_search_results]
                if not persistent.ultra_search_internal:
                    labels = [label for label in labels if not label.startswith("_")]
                return [cls.row(label, label, ["__label__", label]) for label in sorted(labels, key=str.casefold) if cls.match(label, query)][:5000]
            if not query:
                return []
            recursive = persistent.ultra_search_recursive and ultra_search_has_run
            if recursive:
                source = []
                for row in ultra_search_results:
                    try:
                        source.append((row["name"], cls.resolve(row["segments"]), row["segments"]))
                    except Exception:
                        continue
            else:
                source = []
                for name, value in list(store.__dict__.items()):
                    if name.startswith("ultra_search_"):
                        continue
                    if name.startswith("_") and not persistent.ultra_search_internal:
                        continue
                    if name.startswith("ultra_") and not persistent.ultra_search_internal:
                        continue
                    if name in ("renpy", "store", "config", "persistent"):
                        continue
                    if cls.is_runtime_symbol(value):
                        continue
                    source.append((name, value, [name]))
                if persistent.ultra_search_persistent:
                    try:
                        source.extend(("persistent." + name, value, ["__persistent__", name])
                                      for name, value in vars(persistent).items()
                                      if (persistent.ultra_search_internal or not name.startswith(("_", "ultra_")))
                                      and not cls.is_runtime_symbol(value))
                    except Exception:
                        pass
                # Search direct values before traversing objects that may hold
                # aliases to the same game store values (for example build.store).
                source.sort(key=lambda item: 0 if cls.is_supported_value(item[1]) else 1)
            rows, visited = [], set()
            for name, value, segments in source:
                try:
                    cls.walk(name, value, segments, query, mode, rows, visited)
                except Exception:
                    continue
                if len(rows) >= 5000:
                    break
            return sorted(rows, key=lambda row: row["name"].casefold())

        @classmethod
        def resolve(cls, segments):
            if not segments:
                raise KeyError("empty path")
            if segments[0] == "__persistent__":
                value, parts = persistent, segments[1:]
            elif segments[0] == "__label__":
                return segments[1]
            else:
                value, parts = store, segments
            for part in parts:
                value = value[part] if isinstance(value, (dict, list, tuple)) else getattr(value, part)
            return value

        @classmethod
        def set_value(cls, segments, value, restart=True):
            if not segments or segments[0] == "__label__":
                return False
            if segments[0] == "__persistent__":
                parent, parts = persistent, segments[1:]
            else:
                parent, parts = store, segments

            path = []
            for part in parts[:-1]:
                path.append((parent, part))
                parent = parent[part] if isinstance(parent, (dict, list, tuple)) else getattr(parent, part)

            def assign(container, key, new_value):
                if isinstance(container, (dict, list)):
                    container[key] = new_value
                    return None
                if isinstance(container, tuple):
                    items = list(container)
                    items[key] = new_value
                    if type(container) is tuple:
                        return tuple(items)
                    if hasattr(container, "_fields"):
                        return type(container)(*items)
                    return type(container)(items)
                setattr(container, key, new_value)
                return None

            replacement = assign(parent, parts[-1], value)
            for container, key in reversed(path):
                if replacement is None:
                    break
                replacement = assign(container, key, replacement)
            if replacement is not None:
                raise TypeError(ultra_t('saves.could_not_replace_an_immutable_value'))
            if restart:
                renpy.restart_interaction()
            return True

        @staticmethod
        def is_frozen(segments):
            try:
                return tuple(segments) in store.ultra_search_frozen
            except (TypeError, AttributeError):
                return False

        @staticmethod
        def set_frozen(segments, value, enabled):
            key = tuple(segments)
            # Keep a separate copy: the game may mutate a list or dictionary in place.
            previous = getattr(store, "ultra_search_frozen", None)
            updated = dict(previous) if isinstance(previous, dict) else {}
            if enabled:
                updated[key] = _ultra_search_copy.deepcopy(value)
            else:
                updated.pop(key, None)
            store.ultra_search_frozen = updated

    def ultra_search_enforce_freezes(refresh=False):
        changed = False
        frozen = getattr(store, "ultra_search_frozen", None)
        if not isinstance(frozen, dict):
            return
        for segments, frozen_value in tuple(frozen.items()):
            try:
                current = UltraSearchService.resolve(segments)
                if type(current) is type(frozen_value) and current == frozen_value:
                    continue
                UltraSearchService.set_value(segments, _ultra_search_copy.deepcopy(frozen_value), restart=False)
                changed = True
            except Exception:
                # A path may temporarily disappear while changing scenes or loading.
                continue
        if changed and refresh:
            renpy.restart_interaction()

    if ultra_search_enforce_freezes not in config.python_callbacks:
        config.python_callbacks.append(ultra_search_enforce_freezes)
    if ultra_search_enforce_freezes not in config.interact_callbacks:
        config.interact_callbacks.append(ultra_search_enforce_freezes)
    if ultra_search_enforce_freezes not in config.after_load_callbacks:
        config.after_load_callbacks.append(ultra_search_enforce_freezes)

    def ultra_search_before_statement(_statement):
        ultra_search_enforce_freezes()

    if ultra_search_before_statement not in config.statement_callbacks:
        config.statement_callbacks.append(ultra_search_before_statement)

    def ultra_search_run(query=None, reset_page=True):
        if query is not None:
            store.ultra_search_query = str(query)
        store.ultra_search_query = str(store.ultra_search_query or "").strip()
        previous_page = store.ultra_search_page
        if not isinstance(previous_page, int) or isinstance(previous_page, bool):
            previous_page = 1
        store.ultra_search_results = UltraSearchService.search(store.ultra_search_query)
        last_page = max(1, (len(store.ultra_search_results) + UltraSearchService.page_size - 1) // UltraSearchService.page_size)
        store.ultra_search_page = 1 if reset_page else min(max(1, previous_page), last_page)
        store.ultra_search_last_query = store.ultra_search_query
        store.ultra_search_last_options = UltraSearchService.options_signature()
        store.ultra_search_has_run = True

    def ultra_search_reset():
        store.ultra_search_query = ""
        ultra_search_clear_results()

    def ultra_search_clear_results():
        store.ultra_search_results = []
        store.ultra_search_page = 1
        store.ultra_search_last_query = None
        store.ultra_search_last_options = None
        store.ultra_search_has_run = False

    def ultra_search_set_mode(mode):
        if mode not in ("variable names", "values", "labels"):
            return
        persistent.ultra_search_type = mode
        ultra_search_clear_results()
        if str(store.ultra_search_query or "").strip() or mode == "labels":
            ultra_search_run()

    def ultra_search_toggle_filter(field):
        if field not in ("ultra_search_persistent", "ultra_search_objects", "ultra_search_internal",
                         "ultra_search_recursive", "ultra_search_wildcards", "ultra_search_unsupported"):
            return
        setattr(persistent, field, not bool(getattr(persistent, field)))
        had_results = store.ultra_search_has_run
        if field != "ultra_search_recursive":
            ultra_search_clear_results()
        if had_results or str(store.ultra_search_query or "").strip() or persistent.ultra_search_type == "labels":
            ultra_search_run()

    def ultra_search_edit(segments, raw_value, freeze=False):
        raw_value = str(raw_value).strip()
        try:
            if raw_value.casefold() == "true":
                value = True
            elif raw_value.casefold() == "false":
                value = False
            elif raw_value.casefold() == "none":
                value = None
            elif raw_value == "set()":
                value = set()
            else:
                value = _ultra_search_ast.literal_eval(raw_value)
        except Exception:
            if raw_value.startswith(("'", '"', "[", "{", "(")):
                renpy.notify(ultra_ui_t('saves.check_the_value_a_bracket_or_quote_is'))
                return
            value = raw_value
        try:
            if freeze:
                hash(tuple(segments))
                _ultra_search_copy.deepcopy(value)
            if not UltraSearchService.set_value(segments, value, restart=False):
                raise ValueError(ultra_t('saves.this_value_cannot_be_changed'))
            UltraSearchService.set_frozen(segments, value, freeze)
            ultra_search_run(reset_page=False)
            renpy.hide_screen("ultra_edit_variable")
            renpy.notify(ultra_ui_t('saves.value_changed_and_frozen') if freeze else ultra_t('saves.variable_value_changed'))
        except Exception as exc:
            renpy.notify(ultra_ui_t('saves.could_not_change_the_value').format(exc))

    class UltraSaveBrowser(object):
        @classmethod
        def slot(cls, page, position):
            if page == "auto":
                return "auto-{}".format(position)
            if page == "quick":
                return "quick-{}".format(position)
            try:
                page = max(1, int(page))
            except (TypeError, ValueError):
                page = 1
            return "{}-{}".format(page, position)

        @classmethod
        def pages(cls, count=5):
            page = persistent.ultra_save_page
            try:
                page = max(1, int(page))
            except Exception:
                page = 1
            count = max(1, int(count))
            first = max(1, page - count // 2)
            return ["auto", "quick"] + list(range(first, first + count))

        @classmethod
        def page_name(cls, page):
            if page == "auto":
                return ultra_t('saves.autosaves')
            if page == "quick":
                return ultra_t('saves.quick_saves')
            names = persistent.ultra_save_page_names
            if not isinstance(names, dict):
                names = {}
            name = names.get(str(page), names.get(page))
            return name if isinstance(name, str) and name.strip() else ultra_t('saves.page').format(page)

        @classmethod
        def slot_name(cls, slot):
            try:
                metadata = renpy.slot_json(slot)
                return str(metadata.get("_save_name") or "") if isinstance(metadata, dict) else ""
            except Exception:
                return ""

        @classmethod
        def previous_page(cls, page):
            if page == "auto":
                return "auto"
            if page == "quick":
                return "auto"
            try:
                return "quick" if int(page) == 1 else int(page) - 1
            except Exception:
                return "quick"

        @classmethod
        def next_page(cls, page):
            if page == "auto":
                return "quick"
            if page == "quick":
                return 1
            try:
                return int(page) + 1
            except Exception:
                return 1

        @classmethod
        def last_page(cls):
            try:
                slots = renpy.list_saved_games(r"^[0-9]+-[0-9]+$", fast=True)
                pages = [int(slot.split("-", 1)[0]) for slot in slots]
                return max(pages) if pages else 1
            except Exception:
                return 1

        @classmethod
        def save(cls, slot, name=None, ask_name=True, confirm_overwrite=True):
            if not _ultra_search_re.fullmatch(r"[1-9][0-9]*-[1-9]", str(slot or "")):
                renpy.notify(ultra_ui_t('saves.manual_saves_are_only_available_on_numbered_pages'))
                return
            if name is None and ask_name:
                renpy.show_screen("ultra_save_name_dialog", slot=slot)
                return
            if confirm_overwrite and renpy.can_load(slot):
                renpy.show_screen("ultra_confirm_dialog", ultra_t('saves.overwrite_the_save_in_slot').format(slot),
                                  Function(cls.save, slot, name, False, False))
                renpy.hide_screen("ultra_save_name_dialog")
                return
            try:
                # The Ultra menu is an overlay, so keep the gameplay screenshot
                # captured when the menu opened instead of capturing this UI.
                renpy.take_screenshot(keep_existing=True)
                renpy.save(slot, str(name or "").strip()[:150])
                renpy.notify(ultra_ui_t('saves.game_saved'))
                renpy.hide_screen("ultra_save_name_dialog")
                renpy.restart_interaction()
            except Exception as exc:
                renpy.notify(ultra_ui_t('saves.could_not_save_the_game').format(exc))

        @classmethod
        def load(cls, slot):
            if not renpy.can_load(slot):
                renpy.notify(ultra_ui_t('saves.there_is_no_save_in_this_slot'))
                return
            renpy.show_screen("ultra_confirm_dialog", ultra_t('saves.load_this_save_unsaved_progress_will_be_lost'),
                              Function(cls.confirmed_load, slot))

        @classmethod
        def confirmed_load(cls, slot):
            if not renpy.can_load(slot):
                renpy.notify(ultra_ui_t('saves.the_save_is_no_longer_there'))
                return
            renpy.load(slot)

        @classmethod
        def delete(cls, slot):
            if renpy.can_load(slot):
                renpy.show_screen("ultra_confirm_dialog", ultra_t('saves.delete_this_save'),
                                  Function(cls.confirmed_delete, slot))
            else:
                renpy.notify(ultra_ui_t('saves.the_save_is_no_longer_there'))

        @classmethod
        def confirmed_delete(cls, slot):
            try:
                renpy.unlink_save(slot)
                renpy.notify(ultra_ui_t('saves.save_deleted'))
                renpy.restart_interaction()
            except Exception as exc:
                renpy.notify(ultra_ui_t('saves.could_not_delete_the_save').format(exc))

        @classmethod
        def copy_or_move(cls, source, destination, move=False):
            if not destination:
                return
            if source == destination:
                renpy.notify(ultra_ui_t('saves.choose_a_different_slot'))
                return
            if not _ultra_search_re.fullmatch(r"[1-9][0-9]*-[1-9]", str(destination)):
                renpy.notify(ultra_ui_t('saves.enter_a_page_and_a_slot_from_1'))
                return
            if not renpy.can_load(source):
                renpy.notify(ultra_ui_t('saves.the_source_save_is_no_longer_there'))
                return
            prompt = ultra_t('saves.overwrite_the_save_in_slot').format(destination) if renpy.can_load(destination) else ultra_t('saves.move_this_save') if move else ultra_t('saves.copy_this_save')
            renpy.show_screen("ultra_confirm_dialog", prompt,
                              Function(cls.confirmed_copy_or_move, source, destination, move))
            renpy.hide_screen("ultra_save_destination")

        @classmethod
        def confirmed_copy_or_move(cls, source, destination, move=False):
            if not renpy.can_load(source):
                renpy.notify(ultra_ui_t('saves.the_source_save_is_no_longer_there'))
                return
            try:
                if move:
                    renpy.rename_save(source, destination)
                    renpy.notify(ultra_ui_t('saves.save_moved'))
                else:
                    renpy.copy_save(source, destination)
                    renpy.notify(ultra_ui_t('saves.save_copied'))
                renpy.restart_interaction()
            except Exception as exc:
                renpy.notify(ultra_ui_t('saves.could_not_save').format(
                    ultra_t('saves.move_the') if move else ultra_t('saves.copy_the'), exc))

        @classmethod
        def rename_page(cls, page, name):
            if page in ("auto", "quick"):
                return
            old_names = persistent.ultra_save_page_names
            try:
                page = max(1, int(page))
                clean_name = str(name or "").strip()[:50]
                names = old_names
                names = dict(names) if isinstance(names, dict) else {}
                if clean_name:
                    names[str(page)] = clean_name
                    names.pop(page, None)
                else:
                    names.pop(str(page), None)
                    names.pop(page, None)
                persistent.ultra_save_page_names = names
                renpy.save_persistent()
                renpy.hide_screen("ultra_rename_save_page")
                renpy.notify(ultra_ui_t('saves.page_renamed') if clean_name else ultra_t('saves.page_name_reset'))
            except Exception as exc:
                persistent.ultra_save_page_names = old_names
                renpy.notify(ultra_ui_t('saves.could_not_rename_the_page').format(exc))

    def ultra_save_newest_slot(include_quick=True):
        try:
            pattern = r"^(?:[0-9]+|auto|quick)-[0-9]+$" if include_quick else r"^(?:[0-9]+|auto)-[0-9]+$"
            slots = renpy.list_saved_games(pattern, fast=True)
            return max(slots, key=lambda slot: renpy.slot_mtime(slot) or 0) if slots else None
        except Exception:
            return None

    def ultra_save_quick_slot():
        try:
            slots = renpy.list_saved_games(r"^quick-[0-9]+$", fast=True)
            return max(slots, key=lambda slot: renpy.slot_mtime(slot) or 0) if slots else None
        except Exception:
            return None

    def ultra_save_time_text(slot):
        try:
            timestamp = renpy.slot_mtime(slot)
            return _ultra_save_time.strftime("%d.%m.%Y · %H:%M", _ultra_save_time.localtime(timestamp)) if timestamp else ""
        except Exception:
            return ""

    def ultra_set_save_page(page):
        if page not in ("auto", "quick"):
            try:
                page = max(1, int(page))
            except (TypeError, ValueError):
                page = 1
        persistent.ultra_save_page = page
        renpy.save_persistent()

style ultra_search_input is ultra_input:
    background None
    ysize ultra_scale_px(28)
    padding (0, 0)
    text_align 0.0

style ultra_search_input_button is button:
    background Solid(ULTRA_COLOR_HOVER)
    hover_background Solid(ULTRA_COLOR_HOVER)
    padding (ultra_scale_px(2), ultra_scale_px(2))

style ultra_search_submit_button is ultra_button:
    background Solid(ULTRA_COLOR_SELECTED)
    hover_background Solid(ULTRA_COLOR_SELECTED_HOVER)

style ultra_search_submit_button_text is ultra_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_search_reset_button is ultra_button:
    background Solid(ULTRA_COLOR_HOVER)
    hover_background Solid(ULTRA_COLOR_SELECTED)

style ultra_search_reset_button_text is ultra_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_search_mode_button is ultra_small_button:
    padding (ultra_scale_px(7), ultra_scale_px(7))

style ultra_search_mode_button_text is ultra_small_button_text:
    size ultra_scale_px(16)

style selected_ultra_search_mode_button_text is ultra_search_mode_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_search_filter_button is ultra_small_button:
    padding (ultra_scale_px(12), ultra_scale_px(8))

style ultra_search_filter_button_text is ultra_small_button_text:
    size ultra_scale_px(18)
    text_align 0.0
    xalign 0.0

style selected_ultra_search_filter_button_text is ultra_search_filter_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_search_result_name is ultra_root:
    font "UltraUniversalMod/Comfortaa/Comfortaa-SemiBold.ttf"
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_search_frozen_badge is ultra_root:
    color ULTRA_COLOR_ACCENT
    size ultra_scale_px(15)

screen ultra_search_tab():
    # The parent menu reserves 304 scaled pixels for padding, navigation and gaps.
    $ _content_width = config.screen_width - ultra_scale_px(304)
    $ _split = _content_width >= ultra_scale_px(960)
    if _split:
        $ _controls_width = ultra_scale_px(420)
        $ _results_width = _content_width - _controls_width - ultra_scale_px(14)
        hbox:
            xfill True
            yfill True
            spacing ultra_scale_px(14)
            frame:
                xsize _controls_width
                yfill True
                background Solid(ULTRA_COLOR_SURFACE)
                padding (ultra_scale_px(16), ultra_scale_px(14))
                use ultra_search_controls(_controls_width - ultra_scale_px(32), False)
            use ultra_search_results_panel(_results_width)
    else:
        $ _controls_height = min(ultra_scale_px(440), max(ultra_scale_px(260), int(config.screen_height * 0.52)))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(10)
            frame:
                xsize _content_width
                ysize _controls_height
                background Solid(ULTRA_COLOR_SURFACE)
                padding (ultra_scale_px(16), ultra_scale_px(14))
                use ultra_search_controls(_content_width - ultra_scale_px(32), True)
            use ultra_search_results_panel(_content_width)

screen ultra_search_controls(inner_width, compact=False):
    $ _filter_columns = 3 if compact and inner_width >= ultra_scale_px(670) else 2 if compact else 1
    $ _filter_rows = 6 // _filter_columns
    $ _input_width = inner_width - ultra_scale_px(32)
    viewport:
        xfill True
        yfill True
        mousewheel True
        draggable True
        pagekeys True
        scrollbars None
        vbox:
            xsize inner_width
            spacing ultra_scale_px(10)
            text ultra_ui_t('nav.search') style "ultra_page_title" substitute False
            text ultra_ui_t('search.variables_values_and_game_labels') style "ultra_description" xfill True substitute False
            text ultra_ui_t('search.query') style "ultra_card_title" substitute False
            frame:
                xfill True
                ysize ultra_scale_px(54)
                background Solid(ULTRA_COLOR_HOVER)
                padding (ultra_scale_px(2), ultra_scale_px(2))
                input value VariableInputValue("ultra_search_query") style "ultra_search_input" xsize _input_width xpos ultra_scale_px(14) yalign 0.5 pixel_width (_input_width - ultra_scale_px(4)) length 120 copypaste True action Function(ultra_search_run)
            grid 2 1:
                xfill True
                spacing ultra_scale_px(8)
                textbutton ultra_ui_t('dialogues.find') style "ultra_search_submit_button" xfill True xmaximum inner_width action Function(ultra_search_run) substitute False
                textbutton ultra_ui_t('search.reset') style "ultra_search_reset_button" xfill True xmaximum inner_width action Function(ultra_search_reset) substitute False
            text ultra_ui_t('search.search_in') style "ultra_card_title" substitute False
            grid 3 1:
                xfill True
                spacing ultra_scale_px(6)
                for mode, label in (("variable names", ultra_ui_t('search.names')), ("values", ultra_ui_t('search.values')), ("labels", ultra_ui_t('search.labels'))):
                    textbutton label substitute False style "ultra_search_mode_button" xfill True xmaximum inner_width selected (persistent.ultra_search_type == mode) action Function(ultra_search_set_mode, mode)
            text ultra_ui_t('search.options') style "ultra_card_title" substitute False
            if compact:
                grid _filter_columns _filter_rows:
                    xfill True
                    spacing ultra_scale_px(6)
                    for field, label in (("ultra_search_persistent", ultra_ui_t('search.persistent')), ("ultra_search_objects", ultra_ui_t('search.nested_objects')), ("ultra_search_internal", ultra_ui_t('search.internal_names')), ("ultra_search_recursive", ultra_ui_t('search.search_within_results')), ("ultra_search_wildcards", ultra_ui_t('search.patterns_and')), ("ultra_search_unsupported", ultra_ui_t('search.unsupported_types'))):
                        textbutton label substitute False style "ultra_search_filter_button" xfill True xmaximum inner_width selected getattr(persistent, field) sensitive (persistent.ultra_search_type != "labels" or field in ("ultra_search_internal", "ultra_search_recursive", "ultra_search_wildcards")) action Function(ultra_search_toggle_filter, field)
            else:
                vbox:
                    xfill True
                    spacing ultra_scale_px(6)
                    for field, label in (("ultra_search_persistent", ultra_ui_t('search.persistent')), ("ultra_search_objects", ultra_ui_t('search.nested_objects')), ("ultra_search_internal", ultra_ui_t('search.internal_names')), ("ultra_search_recursive", ultra_ui_t('search.search_within_results')), ("ultra_search_wildcards", ultra_ui_t('search.patterns_and')), ("ultra_search_unsupported", ultra_ui_t('search.unsupported_types'))):
                        textbutton label substitute False style "ultra_search_filter_button" xfill True xmaximum inner_width selected getattr(persistent, field) sensitive (persistent.ultra_search_type != "labels" or field in ("ultra_search_internal", "ultra_search_recursive", "ultra_search_wildcards")) action Function(ultra_search_toggle_filter, field)

screen ultra_search_results_panel(panel_width):
    $ _page_size = UltraSearchService.page_size
    $ _page_count = max(1, (len(ultra_search_results) + _page_size - 1) // _page_size)
    $ _page = ultra_search_page if isinstance(ultra_search_page, int) and not isinstance(ultra_search_page, bool) and ultra_search_page > 0 else 1
    $ _page = min(_page, _page_count)
    $ _first = (_page - 1) * _page_size
    $ _current = ultra_search_has_run and ultra_search_last_query == ultra_search_query and ultra_search_last_options == UltraSearchService.options_signature()
    $ _show_results = _current and bool(ultra_search_results)
    frame:
        xsize panel_width
        yfill True
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(14), ultra_scale_px(12))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(8)
            fixed:
                xfill True
                ysize ultra_scale_px(46)
                text ultra_ui_t('search.results') style "ultra_label_text" yalign 0.5 substitute False
                if _show_results and _page_count > 1:
                    hbox:
                        xalign 1.0
                        yalign 0.5
                        spacing ultra_scale_px(8)
                        textbutton ultra_ui_t('common.back') style "ultra_small_button" xsize ultra_scale_px(104) sensitive (_page > 1) action SetField(store, "ultra_search_page", _page - 1) substitute False
                        textbutton ultra_ui_t('common.next') style "ultra_small_button" xsize ultra_scale_px(104) sensitive (_page < _page_count) action SetField(store, "ultra_search_page", _page + 1) substitute False
            if _show_results:
                text ultra_ui_t('search.found_len_ultra_search_results_page_page_of').format(len(ultra_search_results), _page, _page_count) style "ultra_description" substitute False
                viewport:
                    xfill True
                    yfill True
                    mousewheel True
                    draggable True
                    pagekeys True
                    scrollbars None
                    vbox:
                        xfill True
                        spacing ultra_scale_px(7)
                        for row in ultra_search_results[_first:_first + _page_size]:
                            $ _editable = bool(row.get("segments")) and row["segments"][0] != "__label__"
                            $ _text_width = panel_width - ultra_scale_px(196 if _editable else 52)
                            frame:
                                xfill True
                                yfill False
                                background Solid(ULTRA_COLOR_SURFACE_ALT)
                                padding (ultra_scale_px(12), ultra_scale_px(10))
                                hbox:
                                    spacing ultra_scale_px(12)
                                    vbox:
                                        xsize _text_width
                                        spacing ultra_scale_px(5)
                                        text row["name"] substitute False style "ultra_search_result_name" xfill True
                                        text "{}: {}".format(row.get("type", ultra_ui_t('search.value')), UltraSearchService.display_value(row.get("value"), 180)) substitute False style "ultra_description" xfill True
                                        if UltraSearchService.is_frozen(row["segments"]):
                                            text ultra_ui_t('search.frozen') style "ultra_search_frozen_badge" substitute False
                                    if _editable:
                                        textbutton ultra_ui_t('search.edit') style "ultra_small_button" xsize ultra_scale_px(132) yalign 0.5 action Show("ultra_edit_variable", path=row["name"], segments=row["segments"], value=repr(row["value"])) substitute False
            else:
                frame:
                    xfill True
                    yfill True
                    background Solid(ULTRA_COLOR_SURFACE_ALT)
                    padding (ultra_scale_px(18), ultra_scale_px(14))
                    text (ultra_ui_t('search.nothing_found_try_another_query') if _current else ultra_ui_t('search.enter_a_query_and_press_find_or_enter') if not ultra_search_query else ultra_ui_t('search.press_find_or_enter_to_refresh_the_results')) style "ultra_description" xalign 0.5 yalign 0.5 xmaximum ultra_scale_px(620) text_align 0.5 substitute False

screen ultra_search_options():
    modal True
    zorder 250
    key "K_ESCAPE" action Hide("ultra_search_options")
    frame:
        xalign 0.5
        yalign 0.5
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            spacing ultra_scale_px(8)
            text ultra_ui_t('search.search_options') style "ultra_label_text" substitute False
            for mode, title in (("variable names", ultra_ui_t('search.variable_names')), ("values", ultra_ui_t('search.values')), ("labels", ultra_ui_t('search.labels_and_scenes'))):
                textbutton title substitute False style "ultra_button" selected (persistent.ultra_search_type == mode) action [Function(ultra_search_set_mode, mode), Hide("ultra_search_options")]
            text ultra_ui_t('search.r_search_previous_results_p_persistent_variables_o') style "ultra_description" xmaximum ultra_scale_px(800) substitute False
            textbutton ultra_ui_t('common.close') style "ultra_button" xalign 1.0 action Hide("ultra_search_options") substitute False

screen ultra_edit_variable(path, segments, value):
    modal True
    zorder 260
    default edited_value = value
    default freeze_enabled = UltraSearchService.is_frozen(segments)
    $ _dialog_width = min(ultra_scale_px(700), config.screen_width - ultra_scale_px(120))
    $ _input_width = _dialog_width - ultra_scale_px(32)
    key "K_ESCAPE" action Hide("ultra_edit_variable")
    on "show" action ScreenVariableInputValue("edited_value").Enable()
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width + ultra_scale_px(44)
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xsize _dialog_width
            spacing ultra_scale_px(10)
            text ultra_ui_t('search.edit_value') style "ultra_label_text" substitute False
            text str(path) substitute False style "ultra_description" xsize _dialog_width
            button:
                style "ultra_search_input_button"
                xsize _dialog_width
                ysize ultra_scale_px(54)
                action ScreenVariableInputValue("edited_value").Enable()
                input value ScreenVariableInputValue("edited_value") style "ultra_search_input" xsize _input_width xpos ultra_scale_px(14) yalign 0.5 pixel_width (_input_width - ultra_scale_px(4)) length 800 copypaste True action Function(ultra_search_edit, segments, edited_value, freeze_enabled)
            text ultra_ui_t('search.enter_a_string_without_quotes_use_python_syntax') style "ultra_description" xsize _dialog_width substitute False
            textbutton (ultra_ui_t('search.unfreeze') if freeze_enabled else ultra_ui_t('search.freeze_value')) style "ultra_search_filter_button" selected freeze_enabled action SetScreenVariable("freeze_enabled", not freeze_enabled) substitute False
            text ultra_ui_t('search.the_game_restores_the_value_after_actions_it') style "ultra_description" xsize _dialog_width substitute False
            hbox:
                xalign 1.0
                spacing ultra_scale_px(8)
                textbutton ultra_ui_t('search.apply') style "ultra_search_submit_button" action Function(ultra_search_edit, segments, edited_value, freeze_enabled) substitute False
                textbutton ultra_ui_t('common.cancel') style "ultra_button" action Hide("ultra_edit_variable") substitute False

screen ultra_saves_tab():
    $ page_slots = max(9, int(getattr(config, "quicksave_slots", 9) or 9)) if persistent.ultra_save_page == "quick" else max(9, int(getattr(config, "autosave_slots", 9) or 9)) if persistent.ultra_save_page == "auto" else 9
    $ _content_width = config.screen_width - ultra_scale_px(304)
    $ _save_columns = 3 if config.screen_width >= 1600 else 2 if config.screen_width >= 1200 else 1

    if config.screen_width >= 1000:
        vbox:
            xsize _content_width
            yfill True
            spacing ultra_scale_px(10)
            use ultra_save_summary(_content_width)
            use ultra_save_browser(page_slots, _save_columns, _content_width)
    else:
        $ _side_card_width = (_content_width - ultra_scale_px(24)) // 2
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(10)
            frame:
                xfill True
                background Solid(ULTRA_COLOR_SIDEBAR)
                padding (ultra_scale_px(8), ultra_scale_px(8))
                hbox:
                    xfill True
                    spacing ultra_scale_px(8)
                    vbox:
                        xfill True
                        spacing ultra_scale_px(4)
                        text ultra_ui_t('saves.quick_continue') style "ultra_card_title" substitute False
                        $ _quick = ultra_save_quick_slot()
                        use ultra_save_card(_quick or "quick-1", compact=True, save_enabled=False, card_width=_side_card_width)
                    vbox:
                        xfill True
                        spacing ultra_scale_px(4)
                        text ultra_ui_t('saves.other_saves') style "ultra_card_title" substitute False
                        $ _newest = ultra_save_newest_slot(include_quick=False)
                        if _newest:
                            use ultra_save_card(_newest, compact=True, card_width=_side_card_width)
                        else:
                            text ultra_ui_t('saves.no_other_saves_yet') style "ultra_description" substitute False
            use ultra_save_browser(page_slots, _save_columns, _content_width)

screen ultra_save_summary(total_width):
    $ _card_width = (total_width - ultra_scale_px(10)) // 2
    $ _quick = ultra_save_quick_slot()
    $ _newest = ultra_save_newest_slot(include_quick=False)
    hbox:
        spacing ultra_scale_px(10)
        use ultra_save_summary_card(_quick, ultra_ui_t('saves.quick_continue'), _card_width, ultra_ui_t('saves.no_quick_saves_yet'))
        use ultra_save_summary_card(_newest, ultra_ui_t('saves.other_saves'), _card_width, ultra_ui_t('saves.no_other_saves_yet'))

screen ultra_save_summary_card(slot, title, card_width, empty_text):
    $ _exists = bool(slot) and renpy.can_load(slot)
    $ _metadata = renpy.slot_json(slot) if _exists else {}
    $ _metadata = _metadata if isinstance(_metadata, dict) else {}
    $ _thumbnail = renpy.slot_screenshot(slot) if _exists else None
    $ _preview_width = min(ultra_scale_px(228), max(ultra_scale_px(130), card_width // 3))
    frame:
        xsize card_width
        ysize ultra_scale_px(150)
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(10), ultra_scale_px(10))
        hbox:
            xfill True
            yfill True
            spacing ultra_scale_px(12)
            if _exists:
                frame:
                    xsize _preview_width
                    ysize ultra_scale_px(128)
                    background Solid(ULTRA_COLOR_INPUT)
                    padding (0, 0)
                    if _thumbnail:
                        add Transform(_thumbnail, xysize=(_preview_width, ultra_scale_px(128)), fit="contain")
                    else:
                        text ultra_ui_t('saves.no_screenshot') style "ultra_description" xalign 0.5 yalign 0.5 substitute False
            vbox:
                xfill True
                spacing ultra_scale_px(3)
                text title substitute False style "ultra_card_title" xfill True
                if _exists:
                    text str(_metadata.get("_save_name") or slot).replace("{", "{{") substitute False style "ultra_description" xfill True ymaximum ultra_scale_px(34)
                    text ultra_save_time_text(slot) style "ultra_description"
                    textbutton ultra_ui_t('saves.load') style "ultra_save_action_button" xsize ultra_scale_px(150) action Function(UltraSaveBrowser.load, slot) substitute False
                else:
                    text empty_text substitute False style "ultra_description" xfill True

screen ultra_save_browser(page_slots, columns, panel_width):
    $ _rows = (page_slots + columns - 1) // columns
    $ _wide_pager = panel_width >= ultra_scale_px(1160)
    $ _panel_inner_width = panel_width - ultra_scale_px(24)
    $ _pager_gap = ultra_scale_px(6)
    $ _number_width = ultra_scale_px(58)
    $ _fixed_buttons = 6 if _wide_pager else 4
    $ _fixed_width = (ultra_scale_px(90) + ultra_scale_px(112) + ultra_scale_px(300) + ultra_scale_px(130)) if _wide_pager else (ultra_scale_px(90) + ultra_scale_px(112) + ultra_scale_px(200))
    $ _number_count = max(3, min(14, (_panel_inner_width - _fixed_width - _pager_gap * (_fixed_buttons - 1)) // (_number_width + _pager_gap)))
    $ _pages = UltraSaveBrowser.pages(_number_count)
    $ _cell_width = (panel_width - ultra_scale_px(24) - ultra_scale_px(10) * (columns - 1)) // columns
    $ _occupied = sum(1 for position in range(1, page_slots + 1) if renpy.can_load(UltraSaveBrowser.slot(persistent.ultra_save_page, position)))
    $ _grid_viewport_height = config.screen_height - 2 * ultra_scale_px(16) - ultra_scale_px(150) - ultra_scale_px(10) - 2 * ultra_scale_px(10) - ultra_scale_px(48) - ultra_scale_px(56) - 2 * ultra_scale_px(8)
    $ _fit_card_height = (_grid_viewport_height - ultra_scale_px(10) * (_rows - 1)) // _rows
    $ _card_height = max(ultra_scale_px(238), min(ultra_scale_px(242), _fit_card_height))
    frame:
        xsize panel_width
        yfill True
        background Solid(ULTRA_COLOR_SIDEBAR)
        padding (ultra_scale_px(12), ultra_scale_px(10))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(8)
            hbox:
                xsize _panel_inner_width
                ysize ultra_scale_px(48)
                spacing _pager_gap
                textbutton ultra_ui_t('saves.auto') style "ultra_save_page_button" xsize ultra_scale_px(90) selected (persistent.ultra_save_page == "auto") action Function(ultra_set_save_page, "auto") substitute False
                textbutton ultra_ui_t('saves.quick') style "ultra_save_page_button" xsize ultra_scale_px(112) selected (persistent.ultra_save_page == "quick") action Function(ultra_set_save_page, "quick") substitute False
                if _wide_pager:
                    textbutton ultra_ui_t('saves.first') style "ultra_save_page_button" xsize ultra_scale_px(100) action Function(ultra_set_save_page, 1) substitute False
                textbutton ultra_ui_t('common.back') style "ultra_save_page_button" xsize ultra_scale_px(100) sensitive (persistent.ultra_save_page != "auto") action Function(ultra_set_save_page, UltraSaveBrowser.previous_page(persistent.ultra_save_page)) substitute False
                for p in _pages[2:]:
                    textbutton str(p) style "ultra_save_page_button" xsize _number_width selected (persistent.ultra_save_page == p) action Function(ultra_set_save_page, p)
                textbutton ultra_ui_t('common.next') style "ultra_save_page_button" xsize ultra_scale_px(100) action Function(ultra_set_save_page, UltraSaveBrowser.next_page(persistent.ultra_save_page)) substitute False
                if _wide_pager:
                    textbutton ultra_ui_t('saves.last') style "ultra_save_page_button" xsize ultra_scale_px(130) action Function(ultra_set_save_page, UltraSaveBrowser.last_page()) substitute False
            fixed:
                xsize _panel_inner_width
                ysize ultra_scale_px(56)
                vbox:
                    xsize (_panel_inner_width - ultra_scale_px(220))
                    spacing ultra_scale_px(2)
                    text UltraSaveBrowser.page_name(persistent.ultra_save_page).replace("{", "{{") substitute False style "ultra_label_text" xfill True ymaximum ultra_scale_px(30)
                    text ultra_ui_t('saves.used_of_free').format(_occupied, page_slots, page_slots - _occupied, ultra_ui_t('saves.scroll_down_for_more_slots') if page_slots > 9 else "") style "ultra_description" substitute False
                textbutton ultra_ui_t('saves.rename') style "ultra_save_page_button" xsize ultra_scale_px(200) xalign 1.0 yalign 0.5 sensitive (persistent.ultra_save_page not in ("auto", "quick")) action Show("ultra_rename_save_page", page=persistent.ultra_save_page) substitute False
            viewport:
                xfill True
                yfill True
                mousewheel True
                draggable True
                pagekeys True
                scrollbars None
                grid columns _rows:
                    xfill True
                    spacing ultra_scale_px(10)
                    for position in range(1, page_slots + 1):
                        use ultra_save_card(UltraSaveBrowser.slot(persistent.ultra_save_page, position), save_enabled=(persistent.ultra_save_page not in ("auto", "quick")), card_width=_cell_width, card_height=_card_height)
                    for _unused in range((-page_slots) % columns):
                        null

screen ultra_save_card(slot, compact=False, save_enabled=True, card_width=None, card_height=None):
    $ exists = renpy.can_load(slot)
    $ _raw_metadata = renpy.slot_json(slot) if exists else {}
    $ metadata = _raw_metadata if isinstance(_raw_metadata, dict) else {}
    $ _thumbnail = renpy.slot_screenshot(slot) if exists else None
    $ _time_text = ultra_save_time_text(slot) if exists else ""
    $ _preview_width = min(ultra_scale_px(220), max(ultra_scale_px(140), int((card_width or ultra_scale_px(500)) * 0.43)))
    $ _compact_preview_width = min(ultra_scale_px(220), max(ultra_scale_px(100), int(card_width or ultra_scale_px(240)) - ultra_scale_px(20)))
    $ _action_area_width = int(card_width or ultra_scale_px(500)) - ultra_scale_px(20)
    $ _half_action_width = (_action_area_width - ultra_scale_px(5)) // 2
    $ _third_action_width = (_action_area_width - ultra_scale_px(10)) // 3
    frame:
        xfill True
        ysize (ultra_scale_px(230) if compact else (card_height or ultra_scale_px(242)))
        background Solid(ULTRA_COLOR_SURFACE_ALT)
        padding (ultra_scale_px(10), ultra_scale_px(8))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(6)
            if compact:
                if _thumbnail:
                    add Transform(_thumbnail, xysize=(_compact_preview_width, ultra_scale_px(124)), fit="contain")
                else:
                    frame:
                        xfill True
                        ysize ultra_scale_px(124)
                        background Solid(ULTRA_COLOR_INPUT)
                        text (ultra_ui_t('saves.no_screenshot') if exists else ultra_ui_t('saves.empty_slot') if save_enabled else ultra_ui_t('saves.no_quick_save')) style "ultra_description" xalign 0.5 yalign 0.5 substitute False
                if exists:
                    text str(metadata.get('_save_name') or slot).replace("{", "{{") substitute False style "ultra_description" xfill True ymaximum ultra_scale_px(30)
                    textbutton ultra_ui_t('saves.load') style "ultra_save_action_button" xfill True action Function(UltraSaveBrowser.load, slot) substitute False
                elif save_enabled:
                    text str(slot) substitute False style "ultra_description" xfill True ymaximum ultra_scale_px(30)
                    textbutton ultra_ui_t('saves.save') style "ultra_save_action_button" xfill True action Show("ultra_save_name_dialog", slot=slot) substitute False
                else:
                    text ultra_ui_t('saves.no_quick_saves_yet') style "ultra_description" xfill True ymaximum ultra_scale_px(42) substitute False
            else:
                vbox:
                    xfill True
                    yfill True
                    spacing ultra_scale_px(8)
                    hbox:
                        xfill True
                        ysize ultra_scale_px(124)
                        spacing ultra_scale_px(10)
                        frame:
                            xsize _preview_width
                            ysize ultra_scale_px(124)
                            background Solid(ULTRA_COLOR_INPUT)
                            padding (0, 0)
                            if _thumbnail:
                                add Transform(_thumbnail, xysize=(_preview_width, ultra_scale_px(124)), fit="contain")
                            else:
                                text ultra_ui_t('saves.no_screenshot_full_card') style "ultra_description" xalign 0.5 yalign 0.5 text_align 0.5 substitute False
                        vbox:
                            xfill True
                            spacing ultra_scale_px(5)
                            text str(metadata.get('_save_name') or (ultra_ui_t('saves.untitled') if exists else ultra_ui_t('saves.empty_slot'))).replace("{", "{{") substitute False style "ultra_card_title" xfill True ymaximum ultra_scale_px(52)
                            text ultra_ui_t('saves.slot').format(slot) style "ultra_description" substitute False
                            if _time_text:
                                text _time_text style "ultra_description"
                    if exists:
                        vbox:
                            xfill True
                            spacing ultra_scale_px(5)
                            hbox:
                                xsize _action_area_width
                                spacing ultra_scale_px(5)
                                textbutton ultra_ui_t('saves.load') style "ultra_save_action_button" xsize (_half_action_width if save_enabled else _action_area_width) action Function(UltraSaveBrowser.load, slot) substitute False
                                if save_enabled:
                                    textbutton ultra_ui_t('saves.overwrite') style "ultra_save_action_button" xsize _half_action_width action Show("ultra_save_name_dialog", slot=slot) substitute False
                            hbox:
                                xsize _action_area_width
                                spacing ultra_scale_px(5)
                                textbutton ultra_ui_t('saves.copy') style "ultra_save_secondary_button" xsize _third_action_width action Show("ultra_save_destination", source=slot, move=False) substitute False
                                textbutton ultra_ui_t('saves.move') style "ultra_save_secondary_button" xsize _third_action_width action Show("ultra_save_destination", source=slot, move=True) substitute False
                                textbutton ultra_ui_t('saves.delete') style "ultra_save_secondary_button" xsize _third_action_width action Function(UltraSaveBrowser.delete, slot) substitute False
                    else:
                        if save_enabled:
                            null yfill True
                            textbutton ultra_ui_t('saves.save_in_this_slot') style "ultra_save_action_button" xsize _action_area_width ysize ultra_scale_px(44) action Show("ultra_save_name_dialog", slot=slot) substitute False
                        else:
                            text ultra_ui_t('saves.the_game_saves_on_this_page') style "ultra_description" xalign 0.5 yalign 0.5 substitute False

style ultra_save_action_button is ultra_small_button:
    xmaximum None
    yminimum ultra_scale_px(40)
    padding (ultra_scale_px(10), ultra_scale_px(6))
    background Solid(ULTRA_COLOR_HOVER)
    hover_background Solid(ULTRA_COLOR_SELECTED)

style ultra_save_action_button_text is ultra_small_button_text:
    xmaximum None
    size ultra_scale_px(18)
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_save_secondary_button is ultra_save_action_button:
    padding (ultra_scale_px(6), ultra_scale_px(6))
    background Solid(ULTRA_COLOR_SURFACE)
    hover_background Solid(ULTRA_COLOR_HOVER)

style ultra_save_secondary_button_text is ultra_save_action_button_text:
    size ultra_scale_px(17)

style ultra_save_page_button is ultra_small_button:
    xmaximum None
    yminimum ultra_scale_px(48)
    padding (ultra_scale_px(10), ultra_scale_px(7))

style ultra_save_page_button_text is ultra_small_button_text:
    xmaximum None
    size ultra_scale_px(18)

style selected_ultra_save_page_button_text is ultra_save_page_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

screen ultra_save_input_field(variable, field_width, max_length, submit_action=None):
    $ _input_value = ScreenVariableInputValue(variable)
    $ _text_width = field_width - ultra_scale_px(32)
    button:
        style "ultra_search_input_button"
        xsize field_width
        ysize ultra_scale_px(54)
        action _input_value.Enable()
        input value _input_value style "ultra_search_input" xsize _text_width xpos ultra_scale_px(14) yalign 0.5 pixel_width (_text_width - ultra_scale_px(4)) length max_length copypaste True action submit_action

screen ultra_save_name_dialog(slot):
    modal True
    zorder 260
    default name = UltraSaveBrowser.slot_name(slot) if renpy.can_load(slot) else ""
    $ _dialog_width = min(ultra_scale_px(540), config.screen_width - ultra_scale_px(120))
    key "K_ESCAPE" action Hide("ultra_save_name_dialog")
    on "show" action ScreenVariableInputValue("name").Enable()
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width + ultra_scale_px(40)
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(20), ultra_scale_px(16))
        vbox:
            xsize _dialog_width
            spacing ultra_scale_px(8)
            text ultra_ui_t('saves.save_description') style "ultra_label_text" substitute False
            text ultra_ui_t('saves.slot_label').format(slot) substitute False style "ultra_description"
            use ultra_save_input_field("name", _dialog_width, 150, Function(UltraSaveBrowser.save, slot, name, False))
            hbox:
                spacing ultra_scale_px(6)
                xalign 1.0
                textbutton ultra_ui_t('saves.save') style "ultra_button" action Function(UltraSaveBrowser.save, slot, name, False) substitute False
                textbutton ultra_ui_t('common.cancel') style "ultra_small_button" action Hide("ultra_save_name_dialog") substitute False

screen ultra_rename_save_page(page):
    modal True
    zorder 250
    default name = UltraSaveBrowser.page_name(page)
    $ _dialog_width = min(ultra_scale_px(540), config.screen_width - ultra_scale_px(120))
    key "K_ESCAPE" action Hide("ultra_rename_save_page")
    on "show" action ScreenVariableInputValue("name").Enable()
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width + ultra_scale_px(44)
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xsize _dialog_width
            spacing ultra_scale_px(8)
            text ultra_ui_t('saves.page_name') style "ultra_label_text" substitute False
            text ultra_ui_t('saves.clear_the_field_to_restore_the_default_name') style "ultra_description" xsize _dialog_width substitute False
            use ultra_save_input_field("name", _dialog_width, 50, Function(UltraSaveBrowser.rename_page, page, name))
            hbox:
                xalign 1.0
                textbutton ultra_ui_t('saves.save_name') style "ultra_search_submit_button" action Function(UltraSaveBrowser.rename_page, page, name) substitute False
                textbutton ultra_ui_t('common.cancel') style "ultra_button" action Hide("ultra_rename_save_page") substitute False

screen ultra_save_destination(source, move=False):
    modal True
    zorder 250
    default page = "1"
    default position = "1"
    $ _dialog_width = min(ultra_scale_px(610), config.screen_width - ultra_scale_px(120))
    $ _page_field_width = _dialog_width - ultra_scale_px(172)
    key "K_ESCAPE" action Hide("ultra_save_destination")
    on "show" action ScreenVariableInputValue("page").Enable()
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width + ultra_scale_px(44)
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xsize _dialog_width
            spacing ultra_scale_px(8)
            text If(move, ultra_ui_t('saves.move_save'), ultra_ui_t('saves.copy_save')) style "ultra_label_text" substitute False
            text ultra_ui_t('saves.destination_page_and_slot') style "ultra_description" substitute False
            hbox:
                spacing ultra_scale_px(8)
                vbox:
                    spacing ultra_scale_px(3)
                    text ultra_ui_t('saves.page_label') style "ultra_description" substitute False
                    use ultra_save_input_field("page", _page_field_width, 8)
                vbox:
                    spacing ultra_scale_px(3)
                    text ultra_ui_t('saves.slot_1_9') style "ultra_description" substitute False
                    use ultra_save_input_field("position", ultra_scale_px(160), 1)
            hbox:
                xalign 1.0
                textbutton If(move, ultra_ui_t('saves.move'), ultra_ui_t('saves.copy')) style "ultra_button" action Function(UltraSaveBrowser.copy_or_move, source, "{}-{}".format(page, position), move) substitute False
                textbutton ultra_ui_t('common.cancel') style "ultra_button" action Hide("ultra_save_destination") substitute False

screen ultra_confirm_dialog(message, yes_action):
    modal True
    zorder 300
    $ _dialog_width = min(ultra_scale_px(350 if len(message) < 35 else 420 if len(message) < 65 else 500), config.screen_width - ultra_scale_px(80))
    key "K_ESCAPE" action Hide("ultra_confirm_dialog")
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xfill True
            spacing ultra_scale_px(10)
            text message substitute False style "ultra_description" xfill True
            hbox:
                xalign 1.0
                spacing ultra_scale_px(8)
                textbutton ultra_ui_t('saves.confirm') style "ultra_search_submit_button" action [yes_action, Hide("ultra_confirm_dialog")] substitute False
                textbutton ultra_ui_t('common.cancel') style "ultra_button" action Hide("ultra_confirm_dialog") substitute False
