# Ultra Dialogues: per-save viewed lines and a read-only script index.

default ultra_dialogue_chunks = []
default persistent.ultra_dialogue_export_sources = False

init -3 python:
    import datetime as _ultra_dialogue_datetime
    import os as _ultra_dialogue_os
    import re as _ultra_dialogue_re
    import uuid as _ultra_dialogue_uuid

    class UltraDialogues(object):
        CHUNK_SIZE = 96
        PAGE_SIZE = 20
        SPEAKER_PAGE_SIZE = 100
        CONTEXT_SIZE = 3

        # Interface state and the AST index are intentionally not part of a save.
        mode = "mine"
        query = ""
        speaker = None
        page = 0
        matches = []
        _rows_cache = None
        _rows_key = None
        _groups = {}
        _speakers = []
        _scroll = ui.adjustment()

        @classmethod
        def page_size(cls):
            return cls.SPEAKER_PAGE_SIZE if cls.speaker is not None else cls.PAGE_SIZE

        @classmethod
        def _reset_scroll(cls):
            cls._scroll.change(0)

        @classmethod
        def _in_story(cls):
            try:
                return (len(renpy.game.contexts) == 1 and
                        not getattr(store, "main_menu", False) and
                        isinstance(getattr(store, "ultra_dialogue_chunks", None), list))
            except Exception:
                return False

        @classmethod
        def _current_node(cls):
            try:
                return renpy.game.script.namemap.get(renpy.game.context().current)
            except Exception:
                return None

        @classmethod
        def _source(cls):
            node = cls._current_node()
            if node is None:
                return ""
            filename = str(getattr(node, "filename", "") or "").replace("\\", "/")
            line = getattr(node, "linenumber", None)
            if not filename or not isinstance(line, int):
                return ""
            return "{}:{}".format(filename, line)

        @classmethod
        def _static_speaker(cls, who):
            if who is None or who == "":
                return "Рассказчик"
            token = str(who)
            if token[:1] in ("'", '"') and token[-1:] == token[:1]:
                return token[1:-1]
            if _ultra_dialogue_re.match(r"^[A-Za-z_][A-Za-z_0-9]*$", token):
                character = getattr(store, token, None)
                if isinstance(character, renpy.character.ADVCharacter) and not character.dynamic:
                    name = character.name
                    if isinstance(name, str) and "[" not in name:
                        return name
            return token

        @classmethod
        def _append(cls, who, what, source=""):
            if not cls._in_story():
                return
            if not isinstance(what, str) or not what.strip():
                return
            chunks = store.ultra_dialogue_chunks
            if not isinstance(chunks, list):
                chunks = store.list()
                store.ultra_dialogue_chunks = chunks
            if not chunks or not isinstance(chunks[-1], list) or len(chunks[-1]) >= cls.CHUNK_SIZE:
                chunks.append(store.list())
            chunks[-1].append((str(who or "Рассказчик"), what, str(source or "")))
            cls._rows_key = None

        @classmethod
        def history_callback(cls, entry):
            # 'current' is temporary and would duplicate the completed entry.
            if getattr(entry, "kind", None) not in ("adv", "nvl"):
                return
            cls._append(getattr(entry, "who", None), getattr(entry, "what", None), cls._source())

        @classmethod
        def character_callback(cls, event, **kwargs):
            # add_history() returns early when history is disabled. In that
            # case the character's end event is the completed-line signal.
            if event != "end" or not cls._in_story():
                return
            if getattr(config, "history_length", None) is not None and getattr(store, "_history", True):
                return
            node = cls._current_node()
            who = cls._static_speaker(getattr(node, "who", None))
            cls._append(who, kwargs.get("what"), cls._source())

        @classmethod
        def after_load(cls):
            cls.mode = "mine"
            cls.query = ""
            cls.speaker = None
            cls.page = 0
            cls._rows_cache = None
            cls._rows_key = None
            cls.matches = []
            cls._groups = {}
            cls._speakers = []
            cls._reset_scroll()

        @classmethod
        def _journal_key(cls):
            chunks = getattr(store, "ultra_dialogue_chunks", ())
            if not isinstance(chunks, (list, tuple)) or not chunks:
                return ("mine", 0, 0, None)
            last = chunks[-1]
            if not isinstance(last, (list, tuple)):
                return ("mine", len(chunks), 0, None)
            return ("mine", len(chunks), len(last), id(last[-1]) if last else None)

        @classmethod
        def _journal_rows(cls):
            result = []
            chunks = getattr(store, "ultra_dialogue_chunks", ())
            for chunk in chunks if isinstance(chunks, (list, tuple)) else ():
                if not isinstance(chunk, (list, tuple)):
                    continue
                for entry in chunk:
                    if not isinstance(entry, (list, tuple)) or len(entry) < 2 or not isinstance(entry[1], str):
                        continue
                    who, what = entry[:2]
                    source = entry[2] if len(entry) > 2 else ""
                    result.append({"who": str(who or "Рассказчик"), "text": what, "source": str(source or ""),
                                   "group": "journal", "ordinal": len(result)})
            return result

        @classmethod
        def _game_file(cls, filename):
            path = str(filename or "").replace("\\", "/").lower()
            if not path.endswith((".rpy", ".rpyc")):
                return False
            if "/tl/" in path or path.startswith("tl/") or "ultrauniversalmod" in path:
                return False
            return path.startswith("game/") or "/game/" in path

        @classmethod
        def _say_nodes(cls, unit):
            if isinstance(unit, renpy.ast.Say):
                return [unit]
            return [node for node in getattr(unit, "block", ())
                    if isinstance(node, renpy.ast.Say)]

        @classmethod
        def _ast_rows(cls, language):
            result = []
            translator = renpy.game.script.translator
            seen_units = set()

            def add_unit(unit, group):
                identifier = getattr(unit, "identifier", None)
                if identifier and identifier in seen_units:
                    return
                if identifier:
                    seen_units.add(identifier)
                display = translator.language_translates.get((identifier, language), unit) if language else unit
                source_lines = cls._say_nodes(unit)
                source = source_lines[0] if source_lines else unit
                location = "{}:{}".format(source.filename, source.linenumber)
                for say in cls._say_nodes(display):
                    raw = say.what
                    if display is unit and language:
                        raw = renpy.translate_string(raw, language)
                    result.append({"who": cls._static_speaker(say.who),
                                   "text": str(raw), "source": location,
                                   "group": group, "ordinal": len(result)})

            def walk(block, path):
                segment = 0
                for node in block:
                    group = (path, segment)
                    if isinstance(node, (renpy.ast.Translate, renpy.ast.TranslateSay)):
                        if getattr(node, "language", None) is None:
                            add_unit(node, group)
                    elif isinstance(node, renpy.ast.Say):
                        add_unit(node, group)
                    else:
                        # Only consecutive dialogue units are certain context.
                        segment += 1
                        if isinstance(node, renpy.ast.If):
                            for i, (_, child) in enumerate(node.entries):
                                walk(child, path + (("if", node.name, i),))
                        elif isinstance(node, renpy.ast.Menu):
                            for i, (_, _, child) in enumerate(node.items):
                                if child:
                                    walk(child, path + (("menu", node.name, i),))
                        elif isinstance(node, renpy.ast.While):
                            walk(node.block, path + (("while", node.name),))
                        segment += 1

            for node in renpy.game.script.all_stmts:
                if isinstance(node, renpy.ast.Label) and cls._game_file(node.filename):
                    walk(node.block, (node.name,))
            return result

        @classmethod
        def rows(cls):
            language = renpy.game.preferences.language if cls.mode == "all" else None
            key = ("all", language) if cls.mode == "all" else cls._journal_key()
            if key != cls._rows_key or cls._rows_cache is None:
                cls._rows_cache = cls._ast_rows(language) if cls.mode == "all" else cls._journal_rows()
                cls._rows_key = key
                cls._groups = {}
                speakers = set()
                for i, row in enumerate(cls._rows_cache):
                    cls._groups.setdefault(row["group"], []).append(i)
                    speakers.add(row["who"])
                cls._speakers = sorted(speakers, key=lambda value: value.casefold())
                cls._filter()
            return cls._rows_cache

        @classmethod
        def _filter(cls):
            term = cls.query.strip().casefold()
            cls.matches = [i for i, row in enumerate(cls._rows_cache or ())
                           if (not term or term in row["text"].casefold()) and
                           (cls.speaker is None or row["who"] == cls.speaker)]
            cls.page = min(cls.page, max(0, (len(cls.matches) - 1) // cls.page_size()))

        @classmethod
        def search(cls):
            cls.rows()
            cls.page = 0
            cls._filter()
            cls._reset_scroll()
            renpy.restart_interaction()

        @classmethod
        def set_mode(cls, mode):
            if mode not in ("mine", "all"):
                return
            cls.mode = mode
            cls.speaker = None
            cls.page = 0
            cls._rows_key = None
            cls.rows()
            cls._reset_scroll()
            renpy.restart_interaction()

        @classmethod
        def set_speaker(cls, speaker):
            cls.speaker = speaker
            cls.page = 0
            cls._filter()
            cls._reset_scroll()
            renpy.hide_screen("ultra_dialogue_speakers")
            renpy.restart_interaction()

        @classmethod
        def set_page(cls, page):
            cls.page = max(0, int(page))
            cls._reset_scroll()
            renpy.restart_interaction()

        @classmethod
        def page_rows(cls):
            rows = cls.rows()
            start = cls.page * cls.page_size()
            return [(i, rows[i]) for i in cls.matches[start:start + cls.page_size()]]

        @classmethod
        def toggle_export_sources(cls):
            persistent.ultra_dialogue_export_sources = not bool(
                getattr(persistent, "ultra_dialogue_export_sources", False))
            renpy.save_persistent()
            renpy.restart_interaction()

        @classmethod
        def _export_file(cls):
            if cls.speaker is None:
                raise ValueError(ultra_t('dialogues.select_a_character_first'))
            rows = cls.rows()
            selected = [row for row in rows if row["who"] == cls.speaker]
            if not selected:
                raise ValueError(ultra_t('dialogues.this_character_has_no_lines_to_export'))
            savedir = getattr(config, "savedir", None)
            if not savedir:
                raise OSError(ultra_t('dialogues.the_game_s_save_folder_is_unavailable'))

            language = renpy.game.preferences.language
            speaker = (renpy.translate_string(cls.speaker, language)
                       if cls.mode == "all" and language else cls.speaker)
            speaker = str(speaker)
            safe_speaker = _ultra_dialogue_re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", speaker)
            safe_speaker = _ultra_dialogue_re.sub(r"\s+", "_", safe_speaker).strip(" ._")[:48] or "character"
            directory = _ultra_dialogue_os.path.join(savedir, "UltraUniversalMod", "dialogues")
            _ultra_dialogue_os.makedirs(directory, exist_ok=True)
            stamp = _ultra_dialogue_datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = "dialogues-{}-{}-{}-{}.txt".format(
                cls.mode, safe_speaker, stamp, _ultra_dialogue_uuid.uuid4().hex[:8])
            path = _ultra_dialogue_os.path.join(directory, filename)

            with open(path, "x", encoding="utf-8-sig") as output:
                output.write(ultra_t('dialogues.dialogues').format(speaker))
                output.write(ultra_t('dialogues.mode').format(ultra_t('dialogues.my_playthrough') if cls.mode == "mine" else ultra_t('dialogues.entire_game')))
                if cls.mode == "all":
                    output.write(ultra_t('dialogues.order_ast_structure_the_actual_branch_sequence_cannot'))
                else:
                    output.write(ultra_t('dialogues.order_actual_sequence_in_this_playthrough'))
                output.write(ultra_t('dialogues.lines').format(len(selected)))
                for number, row in enumerate(selected, 1):
                    # Text tags are formatting, not dialogue; keep dynamic
                    # placeholders in the static index without evaluating them.
                    line = renpy.text.extras.filter_text_tags(row["text"], allow=set())
                    line = line.replace("{{", "{").replace("\r\n", "\n").replace("\r", "\n")
                    output.write("{}. {}\n".format(number, line.strip().replace("\n", "\n   ")))
                    if persistent.ultra_dialogue_export_sources and row["source"]:
                        output.write(ultra_t('dialogues.source').format(row["source"]))
                    if persistent.ultra_dialogue_export_sources:
                        output.write("\n")
            return path, len(selected)

        @classmethod
        def export_selected(cls):
            try:
                path, count = cls._export_file()
            except (OSError, ValueError) as error:
                renpy.show_screen("ultra_dialogue_export_result", message=ultra_t('dialogues.could_not_save_txt').format(error), path=None)
                return
            renpy.show_screen("ultra_dialogue_export_result",
                              message=ultra_t('dialogues.saved_lines_for_this_character_search_and_page').format(count),
                              path=path)

        @classmethod
        def context(cls, index):
            rows = cls.rows()
            if index < 0 or index >= len(rows):
                return []
            group = cls._groups.get(rows[index]["group"], ())
            try:
                position = group.index(index)
            except ValueError:
                return []
            start = max(0, position - cls.CONTEXT_SIZE)
            end = position + cls.CONTEXT_SIZE + 1
            return [(i, rows[i]) for i in group[start:end]]

        @staticmethod
        def display(value):
            # Keep interpolation and Ren'Py text tags inert in search results.
            return str(value or "").replace("{", "{{")

        @staticmethod
        def display_speaker(value):
            # Keep the journal's stored speaker value independent of Ultra's UI language.
            return UltraDialogues.display(ultra_t('dialogues.narrator') if value == "Рассказчик" else value)

    if UltraDialogues.history_callback not in config.history_callbacks:
        config.history_callbacks.append(UltraDialogues.history_callback)
    if UltraDialogues.character_callback not in config.all_character_callbacks:
        config.all_character_callbacks.append(UltraDialogues.character_callback)
    if UltraDialogues.after_load not in config.after_load_callbacks:
        config.after_load_callbacks.append(UltraDialogues.after_load)

style ultra_dialogue_card is button:
    background Solid(ULTRA_COLOR_SURFACE)
    hover_background Solid(ULTRA_COLOR_HOVER)
    padding (ultra_scale_px(15), ultra_scale_px(12))
    xfill True

style ultra_dialogue_card_text is ultra_root:
    color ULTRA_COLOR_TEXT

style ultra_dialogue_speaker_button is button:
    background Solid(ULTRA_COLOR_SURFACE_ALT)
    hover_background Solid(ULTRA_COLOR_HOVER)
    selected_background Solid(ULTRA_COLOR_SELECTED)
    padding (ultra_scale_px(12), ultra_scale_px(8))
    yminimum ultra_scale_px(46)
    xfill True

style ultra_dialogue_export_toggle is button:
    background Solid(ULTRA_COLOR_SURFACE_ALT)
    hover_background Solid(ULTRA_COLOR_HOVER)
    padding (ultra_scale_px(11), ultra_scale_px(8))
    yminimum ultra_scale_px(42)

screen ultra_dialogues_tab():
    $ _rows = UltraDialogues.rows()
    $ _page_rows = UltraDialogues.page_rows()
    $ _pages = max(1, (len(UltraDialogues.matches) + UltraDialogues.page_size() - 1) // UltraDialogues.page_size())
    $ _width = config.screen_width - ultra_scale_px(304)

    vbox:
        xfill True
        yfill True
        spacing ultra_scale_px(12)

        text ultra_ui_t('nav.dialogues') style "ultra_page_title" substitute False
        hbox:
            spacing ultra_scale_px(8)
            textbutton ultra_ui_t('dialogues.my_playthrough') style "ultra_button" selected (UltraDialogues.mode == "mine") action Function(UltraDialogues.set_mode, "mine") substitute False
            textbutton ultra_ui_t('dialogues.entire_game') style "ultra_button" selected (UltraDialogues.mode == "all") action Function(UltraDialogues.set_mode, "all") substitute False
        if UltraDialogues.mode == "all":
            frame:
                xfill True
                background Solid(ULTRA_COLOR_ALERT)
                padding (ultra_scale_px(12), ultra_scale_px(9))
                text ultra_ui_t('dialogues.spoilers_this_includes_lines_from_branches_you_have') style "ultra_description" color ULTRA_COLOR_ACCENT substitute False
        else:
            text ultra_ui_t('dialogues.lines_shown_in_this_playthrough_and_saved_with') style "ultra_description" substitute False

        hbox:
            xfill True
            spacing ultra_scale_px(8)
            frame:
                xsize max(ultra_scale_px(180), _width - ultra_scale_px(150))
                ysize ultra_scale_px(48)
                background Solid(ULTRA_COLOR_HOVER)
                padding (ultra_scale_px(10), ultra_scale_px(7))
                input value FieldInputValue(UltraDialogues, "query") style "ultra_search_input" xfill True length 120 copypaste True action Function(UltraDialogues.search)
            textbutton ultra_ui_t('dialogues.find') style "ultra_button" xsize ultra_scale_px(130) action Function(UltraDialogues.search) substitute False
        hbox:
            xfill True
            spacing ultra_scale_px(8)
            textbutton (ultra_ui_t('dialogues.all_characters') if UltraDialogues.speaker is None else UltraDialogues.display_speaker(UltraDialogues.speaker)) style "ultra_small_button" action Show("ultra_dialogue_speakers") substitute False
            text ultra_ui_t('dialogues.found').format(len(UltraDialogues.matches)) style "ultra_description" yalign 0.5 substitute False
            null xfill True
            if _pages > 1:
                textbutton ultra_ui_t('common.back') style "ultra_small_button" sensitive (UltraDialogues.page > 0) action Function(UltraDialogues.set_page, UltraDialogues.page - 1) substitute False
                text ultra_ui_t('common.page_count').format(UltraDialogues.page + 1, _pages) style "ultra_description" yalign 0.5 substitute False
                textbutton ultra_ui_t('common.next') style "ultra_small_button" sensitive (UltraDialogues.page + 1 < _pages) action Function(UltraDialogues.set_page, UltraDialogues.page + 1) substitute False
        hbox:
            spacing ultra_scale_px(8)
            button:
                style "ultra_dialogue_export_toggle"
                action Function(UltraDialogues.toggle_export_sources)
                hbox:
                    spacing ultra_scale_px(8)
                    frame:
                        xysize (ultra_scale_px(22), ultra_scale_px(22))
                        padding (0, 0)
                        background Solid(ULTRA_COLOR_SELECTED if persistent.ultra_dialogue_export_sources else ULTRA_COLOR_HOVER)
                        if persistent.ultra_dialogue_export_sources:
                            text "X" style "ultra_root" size ultra_scale_px(17) color ULTRA_COLOR_TEXT_BRIGHT xalign 0.5 yalign 0.5
                    text ultra_ui_t('dialogues.include_sources') style "ultra_description" yalign 0.5 substitute False
            if UltraDialogues.speaker is not None:
                textbutton ultra_ui_t('dialogues.download_txt') style "ultra_small_button" action Function(UltraDialogues.export_selected) substitute False

        viewport:
            xfill True
            yfill True
            yadjustment UltraDialogues._scroll
            mousewheel True
            draggable True
            pagekeys True
            scrollbars None
            if _page_rows:
                vbox:
                    xsize _width
                    spacing ultra_scale_px(8)
                    for _index, _row in _page_rows:
                        button:
                            style "ultra_dialogue_card"
                            action Show("ultra_dialogue_context", index=_index)
                            vbox:
                                xfill True
                                spacing ultra_scale_px(4)
                                if UltraDialogues.speaker is None:
                                    text UltraDialogues.display_speaker(_row["who"]) substitute False style "ultra_card_title" color ULTRA_COLOR_ACCENT
                                text UltraDialogues.display(_row["text"]) substitute False style "ultra_dialogue_card_text" xfill True
                                if UltraDialogues.speaker is None and _row["source"]:
                                    text UltraDialogues.display(_row["source"]) substitute False style "ultra_description" size ultra_scale_px(14)
            else:
                text (ultra_ui_t('dialogues.no_lines_yet') if not _rows else ultra_ui_t('dialogues.no_matches')) style "ultra_description" substitute False

screen ultra_dialogue_speakers():
    modal True
    zorder 260
    key "K_ESCAPE" action Hide("ultra_dialogue_speakers")
    $ _modal_width = min(ultra_scale_px(540), config.screen_width - ultra_scale_px(80))
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _modal_width
        ysize min(ultra_scale_px(660), config.screen_height - ultra_scale_px(80))
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(18), ultra_scale_px(16))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(10)
            hbox:
                xfill True
                text ultra_ui_t('dialogues.character') style "ultra_page_title" substitute False
                textbutton ultra_ui_t('common.close') style "ultra_small_button" xalign 1.0 action Hide("ultra_dialogue_speakers") substitute False
            viewport:
                xsize _modal_width - ultra_scale_px(36)
                yfill True
                mousewheel True
                draggable True
                scrollbars None
                vbox:
                    xsize _modal_width - ultra_scale_px(36)
                    spacing ultra_scale_px(5)
                    button:
                        style "ultra_dialogue_speaker_button"
                        selected (UltraDialogues.speaker is None)
                        action Function(UltraDialogues.set_speaker, None)
                        text ultra_ui_t('dialogues.all_characters') style "ultra_button_text" substitute False
                    for _name in UltraDialogues._speakers:
                        button:
                            style "ultra_dialogue_speaker_button"
                            selected (UltraDialogues.speaker == _name)
                            action Function(UltraDialogues.set_speaker, _name)
                            text UltraDialogues.display_speaker(_name) substitute False style "ultra_button_text"

screen ultra_dialogue_context(index):
    modal True
    zorder 260
    key "K_ESCAPE" action Hide("ultra_dialogue_context")
    $ _context = UltraDialogues.context(index)
    $ _width = min(ultra_scale_px(960), config.screen_width - ultra_scale_px(80))
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _width
        ysize min(ultra_scale_px(700), config.screen_height - ultra_scale_px(80))
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(20), ultra_scale_px(16))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(12)
            hbox:
                xfill True
                text ultra_ui_t('dialogues.dialogue_context') style "ultra_page_title" substitute False
                textbutton ultra_ui_t('common.close') style "ultra_small_button" xalign 1.0 action Hide("ultra_dialogue_context") substitute False
            if UltraDialogues.mode == "all":
                text ultra_ui_t('dialogues.only_nearby_lines_from_the_same_structural_block') style "ultra_description" substitute False
            viewport:
                xfill True
                yfill True
                mousewheel True
                draggable True
                scrollbars None
                vbox:
                    xfill True
                    spacing ultra_scale_px(8)
                    for _row_index, _row in _context:
                        frame:
                            xfill True
                            background Solid(ULTRA_COLOR_SELECTED if _row_index == index else ULTRA_COLOR_SURFACE_ALT)
                            padding (ultra_scale_px(12), ultra_scale_px(10))
                            vbox:
                                xfill True
                                spacing ultra_scale_px(4)
                                text UltraDialogues.display_speaker(_row["who"]) substitute False style "ultra_card_title" color ULTRA_COLOR_ACCENT
                                text UltraDialogues.display(_row["text"]) substitute False style "ultra_root" xfill True
                                if _row["source"]:
                                    text UltraDialogues.display(_row["source"]) substitute False style "ultra_description" size ultra_scale_px(14)

screen ultra_dialogue_export_result(message, path=None):
    modal True
    zorder 270
    key "K_ESCAPE" action Hide("ultra_dialogue_export_result")
    add Solid("#00000088")
    frame:
        xalign 0.5
        yalign 0.5
        xsize min(ultra_scale_px(900), config.screen_width - ultra_scale_px(80))
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(20), ultra_scale_px(18))
        vbox:
            xfill True
            spacing ultra_scale_px(14)
            text ultra_ui_t('dialogues.export_dialogues') style "ultra_page_title" substitute False
            text UltraDialogues.display(message) substitute False style "ultra_description" xfill True
            if path:
                text UltraDialogues.display(path) substitute False style "ultra_root" xfill True
                textbutton ultra_ui_t('dialogues.copy_path') style "ultra_small_button" action CopyToClipboard(path) substitute False
            textbutton ultra_ui_t('common.close') style "ultra_small_button" action Hide("ultra_dialogue_export_result") substitute False
