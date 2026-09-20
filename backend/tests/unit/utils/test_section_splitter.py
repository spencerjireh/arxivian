"""Tests for the section splitter that feeds Jev request state."""

from src.utils.section_splitter import (
    SECTION_CHAR_CAP,
    appendix_headings,
    body_before_references,
    code_mentions,
    extract_sections,
    normalize_text,
    split_sections,
)

_PAPER = """Attention Is All You Need
Abstract
The dominant sequence transduction models are based on recurrent networks.
1 Introduction
Recurrent neural networks have been established.
3 Model Architecture
Most competitive neural sequence transduction models have an encoder-decoder structure.
3.1 Encoder and Decoder Stacks
The encoder is composed of a stack of N = 6 identical layers.
5 Training
We trained on the standard WMT 2014 English-German dataset.
5.3 Optimizer
We used the Adam optimizer with a learning rate of 0.0004.
6 Results
Our model achieves 28.4 BLEU.
7 Conclusion
We presented the Transformer.
The code we used to train and evaluate our models is available at https://github.com/
tensorflow/tensor2tensor.
References
[1] Jimmy Lei Ba. Layer normalization.
Appendix
A Attention Visualizations
A.1 Example
"""


class TestNormalizeText:
    def test_ligatures_and_hyphenation(self):
        assert normalize_text("eﬃcient trans-\nformer") == "efficient transformer"

    def test_keeps_hyphen_before_space(self):
        assert normalize_text("state-of-the-art\nmodel") == "state-of-the-art\nmodel"


class TestSplitSections:
    def test_canonical_keys(self):
        sections = split_sections(_PAPER)
        assert "encoder-decoder structure" in sections["method"]
        assert "Adam optimizer" in sections["experiments"]
        assert "28.4 BLEU" in sections["results"]
        assert "Attention Is All You Need" in sections["front"]
        assert sections["abstract"].startswith("The dominant")

    def test_subsection_headings_append_to_parent_key(self):
        sections = split_sections(_PAPER)
        # "3.1 Encoder and Decoder Stacks" is not a heading word, so it stays inside method
        assert "3.1 Encoder and Decoder Stacks" in sections["method"]

    def test_long_lines_are_not_headings(self):
        text = "Method " + "x" * 80 + "\nbody\n"
        assert "method" not in split_sections(text)


class TestCandidates:
    def test_code_mentions_join_wrapped_url_and_sentence(self):
        found = code_mentions(_PAPER)
        assert found[0] == "https://github.com/tensorflow/tensor2tensor"
        assert any("code we used" in s for s in found)

    def test_code_mentions_ignore_references(self):
        text = "Body text.\nReferences\nCode available at https://github.com/other/repo\n"
        assert code_mentions(text) == ["https://github.com/other/repo"]  # URL regex spans all text
        assert not any("available" in s and "Code" in s for s in code_mentions(text)[1:])

    def test_appendix_headings(self):
        appendix = split_sections(_PAPER)["appendix"]
        assert appendix_headings(appendix) == ["A Attention Visualizations", "A.1 Example"]

    def test_body_before_references(self):
        assert "Layer normalization" not in body_before_references(_PAPER)


class TestExtractSections:
    def test_uses_headings_when_present(self):
        out = extract_sections(_PAPER, abstract="meta abstract")
        assert out["abstract"] == "meta abstract"
        assert "encoder-decoder" in out["method"]
        assert "Adam" in out["experiments"] and "28.4 BLEU" in out["experiments"]
        assert out["appendix_headings"] == "A Attention Visualizations\nA.1 Example"

    def test_positional_fallback_when_no_method_heading(self):
        body = (
            "Title\nAbstract\nabs\n1 Introduction\nintro\n3 BERT\n"
            + ("m " * 400)
            + "\nReferences\nrefs"
        )
        out = extract_sections(body)
        assert out["method"]  # falls back to the 15-45% slice of the body
        assert "refs" not in out["method"]
        assert out["abstract"] == "abs"

    def test_caps(self):
        text = "1 Method\n" + ("word " * 5000) + "\n"
        out = extract_sections(text)
        assert len(out["method"]) == SECTION_CHAR_CAP

    def test_empty(self):
        assert extract_sections("", abstract="a") == {
            "abstract": "a",
            "method": "",
            "experiments": "",
            "appendix_headings": "",
        }
