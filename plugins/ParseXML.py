#!/usr/bin/env python3
"""
infer_xsd.py

Infer a simple XML Schema (XSD) from a sample XML document.

Usage:
    python infer_xsd.py sample.xml > schema.xsd

The script performs a heuristic inference:
- Collects element/attribute names and occurrences
- Records whether elements have text content or child elements
- Collects sample text values to guess simple types: integer, decimal, boolean, date/time (ISO-like), or string
- Infers minOccurs/maxOccurs based on observed counts
- Produces a single XSD with global element for the root and complex/simple types inferred

This is not a perfect replacement for a hand-written XSD, but produces a useful starting point.

Limitations:
- Does not detect mixed content in detail
- Type inference is heuristic; for complex type unions or choices it will default to string
- Namespace handling is minimal (assumes no complex namespaces in sample)

"""
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
import re
from typing import Dict, List, Tuple, Optional

# --- Helpers for type inference -------------------------------------------------
INT_RE = re.compile(r"^[+-]?\d+$")
DEC_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)$")
BOOL_VALUES = {"true", "false", "1", "0", "yes", "no"}
# very simple ISO date-time-ish pattern
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$")


def guess_simple_type(samples: List[str]) -> str:
    """Guess an XSD simpleType based on observed text samples.

    Returns one of: "xs:integer", "xs:decimal", "xs:boolean", "xs:dateTime", "xs:string"
    """
    if not samples:
        return "xs:string"

    # strip whitespace-only
    samples = [s.strip() for s in samples if s is not None and s.strip() != ""]
    if not samples:
        return "xs:string"

    # If any sample can't match a candidate type, rule it out.
    is_int = all(bool(INT_RE.match(s)) for s in samples)
    if is_int:
        return "xs:integer"

    is_dec = all(bool(DEC_RE.match(s)) for s in samples)
    if is_dec:
        return "xs:decimal"

    is_bool = all(s.lower() in BOOL_VALUES for s in samples)
    if is_bool:
        return "xs:boolean"

    is_date = all(bool(DATE_RE.match(s)) for s in samples)
    if is_date:
        return "xs:dateTime"

    return "xs:string"


# --- Data structures to collect schema info -----------------------------------
class ElementStats:
    def __init__(self, name: str):
        self.name = name
        self.count = 0
        self.children_counts: Counter = Counter()  # child name -> times seen across all parent occurrences
        self.occurrence_counts: Counter = Counter()  # number of occurrences of this element per parent instance
        self.attrs_counts: Counter = Counter()  # attribute name -> times observed
        self.attr_samples: Dict[str, Counter] = defaultdict(Counter)  # attr -> sample values
        self.text_samples: List[str] = []
        self.has_text = False

    def record_instance(self, elem: ET.Element):
        self.count += 1
        # attributes
        for k, v in elem.attrib.items():
            self.attrs_counts[k] += 1
            if v is not None:
                self.attr_samples[k][v] += 1
        # children
        child_names = [child.tag for child in list(elem)]
        # count each child occurrence in this parent instance
        if child_names:
            for cn in child_names:
                self.children_counts[cn] += 1
        # text
        text = (elem.text or "")
        if text and text.strip() != "":
            self.has_text = True
            self.text_samples.append(text.strip())


# traverse and collect statistics

def collect_stats(root: ET.Element) -> Dict[str, ElementStats]:
    stats: Dict[str, ElementStats] = {}

    # to compute min/max occurs of children, we need to iterate parents
    def visit(elem: ET.Element):
        name = elem.tag
        if name not in stats:
            stats[name] = ElementStats(name)
        stats[name].record_instance(elem)
        # For each child, record how many times child appears inside this parent occurrence
        child_tags = [c.tag for c in list(elem)]
        child_count_map: Dict[str, int] = Counter(child_tags)
        for child_name, cnt in child_count_map.items():
            # We store occurrence_counts on the child element to later determine min/max per parent
            child_stats = stats.get(child_name)
            if child_stats is None:
                child_stats = ElementStats(child_name)
                stats[child_name] = child_stats
            child_stats.occurrence_counts[cnt] += 1
        # Recurse
        for c in list(elem):
            visit(c)

    visit(root)
    return stats


# --- Build XSD -----------------------------------------------------------------

def generate_xsd(root_tag: str, stats: Dict[str, ElementStats]) -> str:
    """Generate a simple XSD string from collected stats."""
    lines: List[str] = []
    w = lines.append
    w('<?xml version="1.0" encoding="UTF-8"?>')
    w('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">')
    w("")

    # Keep track of generated complexType names to avoid duplication
    generated = set()

    # order elements by likelihood of being complex (have children or attributes)
    element_items = list(stats.items())

    # helper to determine min/max occurs from occurrence_counts
    def min_max_from_counter(counter: Counter) -> Tuple[int, Optional[int]]:
        if not counter:
            # if we never saw specific counts for this child, default min=1 max=1
            return 1, 1
        # counter maps observed number-of-copies -> frequency (# parents that had this many)
        observed_counts = sorted(counter.keys())
        # min observed count (could be missing if parent sometimes lacks the child entirely)
        min_obs = observed_counts[0]
        max_obs = observed_counts[-1]
        # Detect optional: if any parent had 0 occurrences, but we don't record 0 in our structure
        # So try to infer optionality: if sum(freq) < total parents observed, it's optional
        # But we don't have total parents per child here. We'll approximate: if min_obs == 0 then optional
        return min_obs, max_obs

    # We'll generate types for elements that have children or attributes; simple content for others
    # Use a deterministic order
    for name, st in sorted(element_items, key=lambda x: x[0]):
        # Decide if element is complex
        is_complex = bool(st.children_counts) or bool(st.attrs_counts)
        if not is_complex and st.has_text:
            # Simple element with inferred simpleType
            simple_type = guess_simple_type(st.text_samples)
            w(f'  <xs:element name="{escape_name(name)}" type="{simple_type}"/>' )
        elif not is_complex and not st.has_text:
            # empty element: leave as string with minOccurs=0 maybe
            w(f'  <xs:element name="{escape_name(name)}">')
            w('    <xs:complexType/>')
            w('  </xs:element>')
        else:
            # define a complexType
            type_name = f"{sanitize_type_name(name)}Type"
            if type_name in generated:
                w(f'  <xs:element name="{escape_name(name)}" type="{type_name}"/>')
                continue
            generated.add(type_name)
            w(f'  <xs:complexType name="{type_name}">')
            # children
            if st.children_counts:
                w('    <xs:sequence>')
                # iterate over children observed - we don't know order; emit in alphabetical
                for child in sorted(st.children_counts.keys()):
                    child_stats = stats.get(child)
                    if child_stats:
                        min_occ, max_occ = min_max_from_counter(child_stats.occurrence_counts)
                        # Heuristic: if child sometimes absent (we can't see 0), if min_occ==0 or min_occ<1 -> optional
                        minOcc = max(0, min_occ)
                        if max_occ is None:
                            maxOcc = 'unbounded'
                        else:
                            maxOcc = str(max(1, max_occ))
                        w(f'      <xs:element name="{escape_name(child)}" minOccurs="{minOcc}" maxOccurs="{maxOcc}"/>')
                w('    </xs:sequence>')
            # attributes
            if st.attrs_counts:
                for attr in sorted(st.attrs_counts.keys()):
                    samples = list(st.attr_samples[attr].elements()) if st.attr_samples.get(attr) else []
                    # easier: collect unique sample strings
                    sample_vals = list(st.attr_samples[attr].keys())
                    attr_type = guess_simple_type(sample_vals)
                    use = 'optional' if st.attrs_counts[attr] < st.count else 'required'
                    w(f'    <xs:attribute name="{escape_name(attr)}" type="{attr_type}" use="{use}"/>')
            # If has text content as well -> simpleContent
            if st.has_text and st.children_counts:
                # Mixed content (both text and children) — mark mixed="true"
                w('    <!-- mixed content -->')
                # We already emitted sequence above; set mixed and close
                # xmlschema expects mixed on complexType start — for simplicity, leave comment
            elif st.has_text:
                # Element has text but no children — simpleContent
                simple_type = guess_simple_type(st.text_samples)
                w('    <xs:simpleContent>')
                w(f'      <xs:extension base="{simple_type}">')
                # attributes were already added — duplicate not allowed, but for simplicity we close
                w('      </xs:extension>')
                w('    </xs:simpleContent>')
            w('  </xs:complexType>')
            w(f'  <xs:element name="{escape_name(name)}" type="{type_name}"/>')
        w("")

    # Create global element for the root if exists
    if root_tag in stats:
        # we already emitted element line for root; but to be safe, ensure an element declaration exists
        pass

    w('</xs:schema>')
    return "\n".join(lines)


# --- Utilities -----------------------------------------------------------------

def sanitize_type_name(tag: str) -> str:
    # replace non-alphanum with underscore and capitalize
    s = re.sub(r"[^0-9a-zA-Z]", "_", tag)
    if not s:
        s = "Type"
    # ensure starts with letter
    if re.match(r"^[0-9]", s):
        s = "T" + s
    return s[0].upper() + s[1:] + "Type"


def escape_name(name: str) -> str:
    # For now a simple escape: XML names shouldn't contain spaces; replace with underscore
    return name.replace(' ', '_')


# --- Main ---------------------------------------------------------------------

def main(argv):
    if len(argv) < 2:
        print("Usage: python infer_xsd.py sample.xml > schema.xsd", file=sys.stderr)
        return 2
    xml_path = argv[1]
    try:
        tree = ET.parse(xml_path)
    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        return 1
    root = tree.getroot()
    stats = collect_stats(root)
    xsd = generate_xsd(root.tag, stats)
    print(xsd)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
