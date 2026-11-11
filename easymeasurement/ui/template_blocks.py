# EasyMeasurement - easymeasurement/ui/template_blocks.py
# The block tree of the template editor: selecting, adding, moving and removing blocks.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QTreeWidgetItem

from ..reporting.template_model import block_summary, new_block


TOP_ONLY = ("steps", "logo", "structure", "summary")  # blocks that never stand inside a repeat


class TemplateBlocks:
    """A block sits at the top level or inside a repeat, so a path has one or two parts."""

    # Block tree ----------------------------------------------------------

    def _fill_tree(self, select: tuple[int, ...] | None = None) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        for block in self.template["blocks"]:
            item = QTreeWidgetItem([block_summary(block)])
            self.tree.addTopLevelItem(item)
            for child in block.get("blocks", ()) if block["type"] == "steps" else ():
                item.addChild(QTreeWidgetItem([block_summary(child)]))
        self.tree.expandAll()
        self.tree.blockSignals(False)
        if select is not None:
            self._select(select)
        self._show_form()

    def _select(self, path: tuple[int, ...]) -> None:
        item = self.tree.topLevelItem(path[0])
        if item is not None and len(path) == 2:
            item = item.child(path[1])
        if item is not None:
            self.tree.setCurrentItem(item)

    def path(self) -> tuple[int, ...] | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        parent = item.parent()
        if parent is None:
            return (self.tree.indexOfTopLevelItem(item),)
        return (self.tree.indexOfTopLevelItem(parent), parent.indexOfChild(item))

    def _container(self, path: tuple[int, ...]) -> list:
        blocks = self.template["blocks"]
        return blocks if len(path) == 1 else blocks[path[0]].setdefault("blocks", [])

    def _block(self, path: tuple[int, ...]) -> dict:
        return self._container(path)[path[-1]]

    def add_block(self, kind: str) -> None:
        path = self.path()
        block = new_block(kind)
        if path is None:
            self.template["blocks"].append(block)
            target = (len(self.template["blocks"]) - 1,)
        elif kind in TOP_ONLY:  # none of them may sit inside a repeat
            self.template["blocks"].insert(path[0] + 1, block)
            target = (path[0] + 1,)
        elif len(path) == 1 and self._block(path)["type"] == "steps":
            children = self._block(path).setdefault("blocks", [])
            children.append(block)
            target = (path[0], len(children) - 1)
        else:
            self._container(path).insert(path[-1] + 1, block)
            target = (*path[:-1], path[-1] + 1)
        self._fill_tree(target)
        self._touched()

    def move_block(self, offset: int) -> None:
        path = self.path()
        if path is None:
            return
        container = self._container(path)
        index = path[-1]
        target = index + offset
        if not 0 <= target < len(container):
            return
        container[index], container[target] = container[target], container[index]
        self._fill_tree((*path[:-1], target))
        self._touched()

    def _steps_before(self, index: int) -> int | None:
        """Nearest repeat block next to a top-level block: the one above, else below."""
        blocks = self.template["blocks"]
        for candidate in (index - 1, index + 1):
            if 0 <= candidate < len(blocks) and blocks[candidate]["type"] == "steps":
                return candidate
        return None

    def move_into(self) -> None:
        path = self.path()
        if path is None or len(path) != 1 or self._block(path)["type"] in TOP_ONLY:
            return
        repeat = self._steps_before(path[0])
        if repeat is None:
            return
        blocks = self.template["blocks"]
        block = blocks[path[0]]
        children = blocks[repeat].setdefault("blocks", [])
        if repeat < path[0]:
            children.append(block)
            position = len(children) - 1
        else:
            children.insert(0, block)
            position = 0
            repeat -= 1
        blocks.pop(path[0])
        self._fill_tree((repeat, position))
        self._touched()

    def move_out(self) -> None:
        path = self.path()
        if path is None or len(path) != 2:
            return
        block = self._container(path).pop(path[1])
        self.template["blocks"].insert(path[0] + 1, block)
        self._fill_tree((path[0] + 1,))
        self._touched()

    def remove_block(self) -> None:
        path = self.path()
        if path is None:
            return
        container = self._container(path)
        container.pop(path[-1])
        if container:
            target = (*path[:-1], min(path[-1], len(container) - 1))
        else:
            target = path[:-1] or None
        self._fill_tree(target)
        self._touched()

    def _refresh_label(self) -> None:
        item, path = self.tree.currentItem(), self.path()
        if item is not None:
            item.setText(0, block_summary(self._block(path)))

    def _update_buttons(self) -> None:
        path = self.path()
        selected = path is not None
        self.up_button.setEnabled(selected)
        self.down_button.setEnabled(selected)
        self.remove_button.setEnabled(selected)
        top = selected and len(path) == 1
        self.into_button.setEnabled(
            bool(top) and self._block(path)["type"] not in TOP_ONLY
            and self._steps_before(path[0]) is not None
        )
        self.out_button.setEnabled(selected and len(path) == 2)
