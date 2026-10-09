# Live menu and upcoming conditional-branch inspectors.

init 850 python:
    import copy as _ultra_copy

    class UltraChoiceInspector(object):
        @classmethod
        def current_node(cls):
            try:
                node = renpy.game.script.lookup(renpy.game.context().current)
                return node if isinstance(node, renpy.ast.Menu) else None
            except Exception:
                return None

        @classmethod
        def choices(cls):
            node = cls.current_node()
            result = []
            if node is None:
                return result
            for index, item in enumerate(getattr(node, "items", ())):
                if len(item) >= 3 and item[2]:
                    try:
                        visible = bool(renpy.python.py_eval(item[1]))
                    except Exception:
                        visible = False
                    target = ""
                    for stmt in item[2]:
                        if isinstance(stmt, renpy.ast.Jump):
                            target = stmt.target
                            break
                    result.append({"index": index, "text": renpy.exports.substitute(item[0]),
                                   "condition": item[1], "visible": visible, "target": target,
                                   "code": cls.nodes_to_code(item[2])})
            return result

        @classmethod
        def nodes_to_code(cls, nodes, indent=0):
            out = []
            prefix = " " * indent
            for node in nodes or ():
                kind = type(node).__name__
                if kind == "Python":
                    code = getattr(getattr(node, "code", None), "source", None) or getattr(node, "code", "")
                    out.extend(prefix + line for line in str(code).splitlines())
                elif kind == "Jump":
                    out.append(prefix + "jump " + str(node.target))
                elif kind == "Call":
                    out.append(prefix + "call " + str(getattr(node, "label", "")))
                elif kind == "Say":
                    out.append(prefix + str(getattr(node, "what", "")))
                elif kind == "If":
                    for condition, block in getattr(node, "entries", ()):
                        out.append(prefix + "if {}:".format(condition))
                        out.extend(cls.nodes_to_code(block, indent + 4))
                else:
                    code = getattr(node, "get_code", None)
                    if callable(code):
                        try:
                            out.extend(prefix + line for line in str(code()).splitlines())
                            continue
                        except Exception:
                            pass
                    out.append(prefix + "# {}".format(kind))
            return out

        @classmethod
        def choose(cls, index, bypass=False):
            node = cls.current_node()
            if node is None or not 0 <= index < len(node.items) or not node.items[index][2]:
                renpy.notify(ultra_ui_t('inspectors.this_choice_is_no_longer_available_open_the'))
                return
            item = node.items[index]
            try:
                if not bypass and not renpy.python.py_eval(item[1]):
                    renpy.notify(ultra_ui_t('inspectors.this_option_s_condition_has_changed_refresh_the'))
                    return
                renpy.game.log.rollback_is_fixed = False
                renpy.hide_screen("ultra_choices_modal")
                return renpy.ui.ChoiceReturn(item[0], index, renpy.game.context().current)()
            except Exception as exc:
                renpy.notify(ultra_ui_t('inspectors.could_not_choose_the_option').format(exc))

    class UltraPathInspector(object):
        look_ahead_limit = 20

        @classmethod
        def blocking(cls, node):
            if getattr(node, "interact", False):
                return True
            if isinstance(node, renpy.ast.UserStatement):
                try:
                    return node.get_code() == "pause"
                except Exception:
                    return False
            return False

        @classmethod
        def next_node(cls, node):
            if isinstance(node, renpy.ast.Call):
                label = getattr(node, "label", None)
                if label:
                    return renpy.game.script.lookup(label)
            elif isinstance(node, renpy.ast.Jump):
                try:
                    targets = node.predict()
                    if targets and isinstance(targets[0], renpy.ast.Node):
                        return targets[0]
                except Exception:
                    pass
            return getattr(node, "next", None)

        @classmethod
        def next_if(cls):
            try:
                current = renpy.game.script.lookup(renpy.game.context().current)
                if not cls.blocking(current):
                    return None
                node = cls.next_node(current)
                forceable = True
                for _ in range(cls.look_ahead_limit):
                    if node is None:
                        return None
                    if isinstance(node, renpy.ast.If):
                        return node, forceable
                    if cls.blocking(node):
                        return None
                    if isinstance(node, (renpy.ast.Jump, renpy.ast.Call)):
                        forceable = False
                    node = cls.next_node(node)
            except Exception:
                return None

        @classmethod
        def branches(cls):
            result = []
            found = cls.next_if()
            if not found:
                return result
            node, forceable = found
            active_branch_found = False
            for index, (condition, block) in enumerate(node.entries):
                try:
                    condition_matches = bool(renpy.python.py_eval(condition))
                except Exception:
                    condition_matches = False
                selected = condition_matches and not active_branch_found
                if selected:
                    active_branch_found = True
                target = next((stmt.target for stmt in block if isinstance(stmt, renpy.ast.Jump)), "")
                result.append({"index": index, "condition": condition, "selected": selected,
                               "matches": condition_matches, "forceable": forceable and bool(block), "target": target,
                               "code": UltraChoiceInspector.nodes_to_code(block)})
            return result

        @classmethod
        def force(cls, index):
            found = cls.next_if()
            if not found:
                return False
            node, forceable = found
            if not forceable or UltraChoiceInspector.current_node() is not None:
                return False
            try:
                target = node.entries[index][1][0]
                context = renpy.game.context()
                if context.next_node is node:
                    context.next_node = target
                    return True
                chain = _ultra_copy.copy(context.next_node)
                current = chain
                for _ in range(cls.look_ahead_limit):
                    if current is None or not current.next:
                        break
                    if current.next is node:
                        current.next = target
                        context.next_node = chain
                        return True
                    current.next = _ultra_copy.copy(current.next)
                    current = cls.next_node(current)
            except Exception as exc:
                renpy.log("Ultra path selection failed: {}".format(exc))
            return False

        @classmethod
        def choose(cls, index):
            if cls.force(index):
                renpy.hide_screen("ultra_paths_modal")
                return True
            renpy.notify(ultra_ui_t('inspectors.could_not_take_this_path_choose_another_or'))

screen ultra_choices_modal():
    modal True
    zorder 260
    key "K_ESCAPE" action Hide("ultra_choices_modal")
    $ _choices = UltraChoiceInspector.choices()
    $ _dialog_width = min(int(config.screen_width * 0.82), ultra_scale_px(1120))
    $ _dialog_height = min(int(config.screen_height * 0.80), max(ultra_scale_px(280), ultra_scale_px(150) + len(_choices) * ultra_scale_px(178)))
    $ _compact = _dialog_width < ultra_scale_px(740)
    add Solid("#00000099")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width
        ysize _dialog_height
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(12)
            fixed:
                xfill True
                ysize ultra_scale_px(48)
                text ultra_ui_t('chronology.choice_options') style "ultra_label_text" yalign 0.5 substitute False
                textbutton ultra_ui_t('common.close') style "ultra_button" xsize ultra_scale_px(130) xalign 1.0 yalign 0.5 action Hide("ultra_choices_modal") substitute False
            text ultra_ui_t('inspectors.visible_and_hidden_answers_appear_here_you_can') style "ultra_description" xfill True substitute False
            viewport:
                xfill True
                yfill True
                mousewheel True
                draggable True
                scrollbars None
                pagekeys True
                vbox:
                    xfill True
                    spacing ultra_scale_px(10)
                    if not _choices:
                        text ultra_ui_t('inspectors.no_options_are_available_now_close_this_window') style "ultra_description" xfill True substitute False
                    for choice in _choices:
                        frame:
                            xfill True
                            background Solid(ULTRA_COLOR_SURFACE)
                            padding (ultra_scale_px(16), ultra_scale_px(14))
                            vbox:
                                xfill True
                                spacing ultra_scale_px(8)
                                text "{}. {}".format(choice.get("index", 0) + 1, str(choice.get("text") or ultra_ui_t('inspectors.no_text'))) substitute False style "ultra_card_title" xfill True
                                text (ultra_ui_t('inspectors.available_now') if choice.get("visible", False) else ultra_ui_t('inspectors.condition_not_met')) style "ultra_description" color (ULTRA_COLOR_ACCENT if choice.get("visible", False) else ULTRA_COLOR_TEXT_MUTED) xfill True substitute False
                                if _compact:
                                    hbox:
                                        spacing ultra_scale_px(10)
                                        textbutton ultra_ui_t('inspectors.condition') style "ultra_button" xsize ultra_scale_px(160) action Show("ultra_code_view", title=ultra_ui_t('inspectors.option_condition'), code=choice["condition"]) substitute False
                                        textbutton ultra_ui_t('inspectors.code') style "ultra_button" xsize ultra_scale_px(110) action Show("ultra_code_view", title=ultra_ui_t('inspectors.option_code'), code="\n".join(choice["code"])) substitute False
                                    textbutton (ultra_ui_t('inspectors.choose') if choice.get("visible", False) else ultra_ui_t('inspectors.take_this_answer')) style "ultra_search_submit_button" xsize ultra_scale_px(230) action Function(UltraChoiceInspector.choose, choice["index"], not choice.get("visible", False)) substitute False
                                else:
                                    fixed:
                                        xfill True
                                        ysize ultra_scale_px(46)
                                        textbutton ultra_ui_t('inspectors.condition') style "ultra_button" xsize ultra_scale_px(160) action Show("ultra_code_view", title=ultra_ui_t('inspectors.option_condition'), code=choice["condition"]) substitute False
                                        textbutton ultra_ui_t('inspectors.code') style "ultra_button" xsize ultra_scale_px(110) xpos ultra_scale_px(170) action Show("ultra_code_view", title=ultra_ui_t('inspectors.option_code'), code="\n".join(choice["code"])) substitute False
                                        textbutton (ultra_ui_t('inspectors.choose') if choice.get("visible", False) else ultra_ui_t('inspectors.take_this_answer')) style "ultra_search_submit_button" xsize ultra_scale_px(230) xalign 1.0 action Function(UltraChoiceInspector.choose, choice["index"], not choice.get("visible", False)) substitute False
                    null ysize ultra_scale_px(18)

screen ultra_paths_modal():
    modal True
    zorder 260
    key "K_ESCAPE" action Hide("ultra_paths_modal")
    $ _branches = UltraPathInspector.branches()
    $ _dialog_width = min(int(config.screen_width * 0.82), ultra_scale_px(1120))
    $ _dialog_height = min(int(config.screen_height * 0.80), max(ultra_scale_px(310), ultra_scale_px(178) + len(_branches) * ultra_scale_px(176)))
    $ _compact = _dialog_width < ultra_scale_px(740)
    add Solid("#00000099")
    frame:
        xalign 0.5
        yalign 0.5
        xsize _dialog_width
        ysize _dialog_height
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(12)
            fixed:
                xfill True
                ysize ultra_scale_px(48)
                text ultra_ui_t('inspectors.next_branch') style "ultra_label_text" yalign 0.5 substitute False
                textbutton ultra_ui_t('common.close') style "ultra_button" xsize ultra_scale_px(130) xalign 1.0 yalign 0.5 action Hide("ultra_paths_modal") substitute False
            text ultra_ui_t('inspectors.the_highlighted_path_is_the_one_the_game') style "ultra_description" xfill True substitute False
            viewport:
                xfill True
                yfill True
                mousewheel True
                draggable True
                scrollbars None
                pagekeys True
                vbox:
                    xfill True
                    spacing ultra_scale_px(10)
                    if not _branches:
                        text ultra_ui_t('inspectors.no_conditional_branch_is_nearby_close_this_window') style "ultra_description" xfill True substitute False
                    for branch in _branches:
                        $ _condition_value = branch.get("condition")
                        $ _is_else_branch = not _condition_value or (str(_condition_value).strip() == "True" and branch.get("index") == len(_branches) - 1 and len(_branches) > 1)
                        frame:
                            xfill True
                            background Solid(ULTRA_COLOR_SELECTED if branch.get("selected") else ULTRA_COLOR_SURFACE)
                            padding (ultra_scale_px(16), ultra_scale_px(14))
                            vbox:
                                xfill True
                                spacing ultra_scale_px(8)
                                text (ultra_ui_t('inspectors.fallback_path') if _is_else_branch else ultra_ui_t('inspectors.path').format(branch.get("index", 0) + 1)) style "ultra_card_title" xfill True substitute False
                                if branch.get("selected"):
                                    text ultra_ui_t('inspectors.the_game_will_choose_this_path') style "ultra_description" color ULTRA_COLOR_TEXT_BRIGHT substitute False
                                elif _is_else_branch:
                                    text ultra_ui_t('inspectors.runs_if_the_conditions_above_are_not_met') style "ultra_description" xfill True substitute False
                                elif branch.get("matches"):
                                    text ultra_ui_t('inspectors.condition_met_but_an_earlier_path_was_selected') style "ultra_description" xfill True substitute False
                                else:
                                    text ultra_ui_t('inspectors.condition_not_met_yet') style "ultra_description" xfill True substitute False
                                if not _is_else_branch and _condition_value:
                                    text ultra_ui_t('inspectors.check').format(str(_condition_value)) substitute False style "ultra_description" xfill True
                                if not branch.get("forceable", False) and not branch.get("selected"):
                                    text ultra_ui_t('inspectors.you_can_only_inspect_this_path_from_here') style "ultra_description" xfill True substitute False
                                if _compact:
                                    hbox:
                                        spacing ultra_scale_px(10)
                                        textbutton ultra_ui_t('inspectors.condition') style "ultra_button" xsize ultra_scale_px(160) action Show("ultra_code_view", title=ultra_ui_t('inspectors.branch_condition'), code=branch["condition"]) substitute False
                                        textbutton ultra_ui_t('inspectors.code') style "ultra_button" xsize ultra_scale_px(110) action Show("ultra_code_view", title=ultra_ui_t('inspectors.branch_code'), code="\n".join(branch["code"])) substitute False
                                    if branch.get("selected"):
                                        textbutton ultra_ui_t('inspectors.continue') style "ultra_button" xsize ultra_scale_px(210) action [Hide("ultra_paths_modal"), Return()] substitute False
                                    else:
                                        textbutton ultra_ui_t('inspectors.take_this_path') style "ultra_search_submit_button" xsize ultra_scale_px(230) sensitive branch.get("forceable", False) action Function(UltraPathInspector.choose, branch["index"]) substitute False
                                else:
                                    fixed:
                                        xfill True
                                        ysize ultra_scale_px(46)
                                        textbutton ultra_ui_t('inspectors.condition') style "ultra_button" xsize ultra_scale_px(160) action Show("ultra_code_view", title=ultra_ui_t('inspectors.branch_condition'), code=branch["condition"]) substitute False
                                        textbutton ultra_ui_t('inspectors.code') style "ultra_button" xsize ultra_scale_px(110) xpos ultra_scale_px(170) action Show("ultra_code_view", title=ultra_ui_t('inspectors.branch_code'), code="\n".join(branch["code"])) substitute False
                                        if branch.get("selected"):
                                            textbutton ultra_ui_t('inspectors.continue') style "ultra_button" xsize ultra_scale_px(210) xalign 1.0 action [Hide("ultra_paths_modal"), Return()] substitute False
                                        else:
                                            textbutton ultra_ui_t('inspectors.take_this_path') style "ultra_search_submit_button" xsize ultra_scale_px(230) xalign 1.0 sensitive branch.get("forceable", False) action Function(UltraPathInspector.choose, branch["index"]) substitute False
                    null ysize ultra_scale_px(18)

screen ultra_code_view(title, code):
    modal True
    zorder 280
    key "K_ESCAPE" action Hide("ultra_code_view")
    $ _shown_code = str(code or "").strip() or ultra_ui_t('inspectors.no_additional_code_here')
    $ _dialog_height = min(int(config.screen_height * 0.72), max(ultra_scale_px(260), ultra_scale_px(160) + len(_shown_code.splitlines()) * ultra_scale_px(26)))
    add Solid("#00000099")
    frame:
        xalign 0.5
        yalign 0.5
        xsize min(int(config.screen_width * 0.82), ultra_scale_px(940))
        ysize _dialog_height
        background Solid(ULTRA_COLOR_BACKGROUND)
        padding (ultra_scale_px(22), ultra_scale_px(18))
        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(12)
            fixed:
                xfill True
                ysize ultra_scale_px(48)
                text title substitute False style "ultra_label_text" yalign 0.5
                textbutton ultra_ui_t('common.close') style "ultra_button" xsize ultra_scale_px(130) xalign 1.0 yalign 0.5 action Hide("ultra_code_view") substitute False
            viewport:
                xfill True
                yfill True
                mousewheel True
                draggable True
                scrollbars None
                pagekeys True
                frame:
                    xfill True
                    background Solid(ULTRA_COLOR_SURFACE)
                    padding (ultra_scale_px(16), ultra_scale_px(14))
                    text _shown_code substitute False style "ultra_description" xfill True
