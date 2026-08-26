"""Vue SFC parser — regex-based, extracts data-testid and component info."""

import re
from typing import List, Optional

from .base import BaseParser
from ..models.doc_types import ExtractedApiInfo, ExtractedPageInfo, PageElement


class VueParser(BaseParser):
    """Vue SFC parser — regex-based, extracts data-testid and component info."""

    def extract_api_info(self, code: str, function_name: str) -> Optional[ExtractedApiInfo]:
        """Not applicable for Vue files. Returns None."""
        return None

    def extract_page_info(self, code: str) -> ExtractedPageInfo:
        """Extract data-testid attributes and component name from a .vue file.

        Returns ExtractedPageInfo with component_name and elements list.
        Empty elements list if no template or no testids found.
        """
        template = self._extract_template(code)
        elements = self._extract_testids(template) if template else []
        component_name = self._extract_component_name(code)

        return ExtractedPageInfo(component_name=component_name, elements=elements)

    def _extract_template(self, code: str) -> str:
        """Extract content between <template> and </template> tags."""
        m = re.search(r'<template[^>]*>(.*?)</template>', code, re.DOTALL | re.IGNORECASE)
        return m.group(1) if m else ''

    def _extract_testids(self, template: str) -> List[PageElement]:
        """Extract static and dynamic data-testid values."""
        elements: List[PageElement] = []
        seen: set = set()

        # Static data-testid="value"
        # We need to capture the element tag as well
        # Pattern: <tag-name ... data-testid="value" ...
        static_pattern = re.compile(
            r'<(\w[\w-]*)[^>]*?\s+data-testid="([^"]+)"',
            re.DOTALL,
        )
        for m in static_pattern.finditer(template):
            element_type = m.group(1)
            testid = m.group(2)
            if testid not in seen:
                seen.add(testid)
                elements.append(PageElement(testid=testid, element_type=element_type, is_dynamic=False))

        # Dynamic :data-testid bindings with template literals
        # Pattern: <tag ... :data-testid="`prefix-${...}`" ...
        dynamic_pattern = re.compile(
            r'<(\w[\w-]*)[^>]*?\s+:data-testid="`([^`]*)`"',
            re.DOTALL,
        )
        for m in dynamic_pattern.finditer(template):
            element_type = m.group(1)
            binding = m.group(2)
            # Extract static prefix: everything before the first ${
            prefix_match = re.match(r'^([^$]*?)(?:\$\{|$)', binding)
            prefix = prefix_match.group(1) if prefix_match else binding
            # Remove trailing separator if present
            prefix = prefix.rstrip('-')
            if prefix and prefix not in seen:
                seen.add(prefix)
                elements.append(PageElement(testid=prefix, element_type=element_type, is_dynamic=True))

        # Dynamic :data-testid with single-quoted template literals
        dynamic_pattern_sq = re.compile(
            r"<(\w[\w-]*)[^>]*?\s+:data-testid=\"'([^']*)'\"",
            re.DOTALL,
        )
        for m in dynamic_pattern_sq.finditer(template):
            element_type = m.group(1)
            testid = m.group(2)
            if testid and testid not in seen:
                seen.add(testid)
                elements.append(PageElement(testid=testid, element_type=element_type, is_dynamic=False))

        return elements

    def _extract_component_name(self, code: str) -> str:
        """Extract component name from <script> section or fall back to empty string."""
        # Extract script section
        script_match = re.search(r'<script[^>]*>(.*?)</script>', code, re.DOTALL | re.IGNORECASE)
        if not script_match:
            return ''

        script = script_match.group(1)

        # Try defineComponent({ name: '...' })
        m = re.search(r'defineComponent\s*\(\s*\{[^}]*?name\s*:\s*["\']([^"\']+)["\']', script, re.DOTALL)
        if m:
            return m.group(1)

        # Try export default { name: '...' }
        m = re.search(r'export\s+default\s*\{[^}]*?name\s*:\s*["\']([^"\']+)["\']', script, re.DOTALL)
        if m:
            return m.group(1)

        # Try name: '...' at top level of script
        m = re.search(r'name\s*:\s*["\']([^"\']+)["\']', script)
        if m:
            return m.group(1)

        return ''
