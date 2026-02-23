"""Canned data for eval fixtures (fake chunks, papers, search results)."""

from __future__ import annotations


def make_chunk(
    chunk_id: str = "chunk-1",
    chunk_text: str = "Default chunk text.",
    arxiv_id: str = "2301.00001",
    title: str = "Sample Paper",
    authors: str = "A. Author, B. Researcher",
    section_name: str = "Introduction",
    score: float = 0.9,
    pdf_url: str = "https://arxiv.org/pdf/2301.00001",
    published_date: str = "2023-01-01",
) -> dict:
    """Create a chunk dict matching RetrieveChunksTool output schema."""
    return {
        "chunk_id": chunk_id,
        "chunk_text": chunk_text,
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "section_name": section_name,
        "score": score,
        "pdf_url": pdf_url,
        "published_date": published_date,
    }


TRANSFORMER_CHUNKS = [
    make_chunk(
        chunk_id="chunk-t1",
        chunk_text=(
            "The Transformer follows an encoder-decoder architecture built entirely "
            "on attention mechanisms, dispensing with recurrence and convolutions. "
            "The key innovation is multi-head self-attention: the model projects "
            "queries, keys, and values into h parallel heads, computes scaled "
            "dot-product attention in each, concatenates the results, and applies "
            "a final linear projection. This allows the model to jointly attend to "
            "information from different representation subspaces at different positions."
        ),
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        authors="A. Vaswani, N. Shazeer, N. Parmar et al.",
        section_name="Model Architecture",
    ),
    make_chunk(
        chunk_id="chunk-t2",
        chunk_text=(
            "We trained on the WMT 2014 English-German dataset consisting of about "
            "4.5 million sentence pairs. The Transformer (big) model outperforms the "
            "best previously reported models including ensembles by more than 2.0 BLEU, "
            "establishing a new state-of-the-art BLEU score of 28.4."
        ),
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        authors="A. Vaswani, N. Shazeer, N. Parmar et al.",
        section_name="Results",
    ),
    make_chunk(
        chunk_id="chunk-t3",
        chunk_text=(
            "Positional encodings are added to the input embeddings at the bottoms of "
            "the encoder and decoder stacks. We use sine and cosine functions of different "
            "frequencies: PE(pos,2i) = sin(pos/10000^(2i/d_model)) and "
            "PE(pos,2i+1) = cos(pos/10000^(2i/d_model)). We chose this function because "
            "it allows the model to attend to relative positions, since for any fixed "
            "offset k, PE(pos+k) can be represented as a linear function of PE(pos)."
        ),
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        authors="A. Vaswani, N. Shazeer, N. Parmar et al.",
        section_name="Positional Encoding",
    ),
]

BERT_CHUNKS = [
    make_chunk(
        chunk_id="chunk-b1",
        chunk_text=(
            "BERT is designed to pre-train deep bidirectional representations from "
            "unlabeled text by jointly conditioning on both left and right context in "
            "all layers. The pre-trained BERT model can be fine-tuned with just one "
            "additional output layer for a wide range of tasks."
        ),
        arxiv_id="1810.04805",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors="J. Devlin, M. Chang, K. Lee, K. Toutanova",
        section_name="Introduction",
    ),
    make_chunk(
        chunk_id="chunk-b2",
        chunk_text=(
            "BERT's pre-training uses two objectives: masked language modeling (MLM) "
            "and next sentence prediction (NSP). In MLM, 15% of input tokens are "
            "randomly selected; of those, 80% are replaced with [MASK], 10% with a "
            "random token, and 10% are left unchanged. The model is trained to predict "
            "the original tokens using cross-entropy loss over the full vocabulary."
        ),
        arxiv_id="1810.04805",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors="J. Devlin, M. Chang, K. Lee, K. Toutanova",
        section_name="Pre-training Objectives",
    ),
]

CONTRADICTORY_CHUNKS = [
    make_chunk(
        chunk_id="chunk-contra1",
        chunk_text=(
            "We trained the Transformer (big) model using a batch size of 25,000 "
            "source tokens and 25,000 target tokens per batch on 8 P100 GPUs. "
            "Training took 3.5 days to complete."
        ),
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        authors="A. Vaswani, N. Shazeer, N. Parmar et al.",
        section_name="Training",
    ),
    make_chunk(
        chunk_id="chunk-contra2",
        chunk_text=(
            "Each training batch contained approximately 50,000 tokens total. "
            "The base model was trained for 100,000 steps on 8 P100 GPUs, "
            "which took approximately 12 hours."
        ),
        arxiv_id="1706.03762",
        title="Attention Is All You Need",
        authors="A. Vaswani, N. Shazeer, N. Parmar et al.",
        section_name="Training Details",
    ),
]

IRRELEVANT_CHUNKS = [
    make_chunk(
        chunk_id="chunk-irr1",
        chunk_text=(
            "We propose a novel convolutional neural network architecture for image "
            "classification. The model uses depthwise separable convolutions to reduce "
            "computational cost while maintaining accuracy on ImageNet."
        ),
        arxiv_id="2005.12345",
        title="Efficient Image Classification with Separable Convolutions",
        authors="C. Vision, D. Networks",
        section_name="Architecture",
    ),
]

ARXIV_SEARCH_RESULTS = {
    "total_count": 3,
    "results": [
        {
            "arxiv_id": "1706.03762",
            "title": "Attention Is All You Need",
            "authors": "A. Vaswani et al.",
            "abstract": "The dominant sequence transduction models are based on complex "
            "recurrent or convolutional neural networks...",
            "published": "2017-06-12",
            "pdf_url": "https://arxiv.org/pdf/1706.03762",
        },
        {
            "arxiv_id": "1810.04805",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": "J. Devlin et al.",
            "abstract": "We introduce a new language representation model called BERT...",
            "published": "2018-10-11",
            "pdf_url": "https://arxiv.org/pdf/1810.04805",
        },
    ],
}

LIST_PAPERS_RESULTS = {
    "total_count": 2,
    "papers": [
        {
            "arxiv_id": "1706.03762",
            "title": "Attention Is All You Need",
            "authors": "A. Vaswani et al.",
            "chunk_count": 15,
        },
        {
            "arxiv_id": "1810.04805",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": "J. Devlin et al.",
            "chunk_count": 22,
        },
    ],
}

CITATION_RESULTS = {
    "paper_title": "Attention Is All You Need",
    "arxiv_id": "1706.03762",
    "references": [
        {
            "arxiv_id": "1409.0473",
            "title": "Neural Machine Translation by Jointly Learning to Align and Translate",
        },
        {"arxiv_id": "1412.6980", "title": "Adam: A Method for Stochastic Optimization"},
    ],
    "cited_by": [
        {
            "arxiv_id": "1810.04805",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        },
    ],
}
