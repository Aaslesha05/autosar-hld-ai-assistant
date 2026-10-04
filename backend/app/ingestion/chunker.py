"""
chunker.py
----------
Intelligent context-aware chunking engine for AUTOSAR High Level Design (HLD) documents.

Preserves:
- Document -> Page -> Section Heading -> Chunk traceability
- Tabular data as structured Markdown blocks
- OCR status and source page numbers
- Configurable chunk size and overlap with sentence/word boundary protection
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.core.config import settings
from app.schemas.page import DocumentPageResponse, TableData
from app.schemas.chunk import Chunk, ChunkMetadata

logger = logging.getLogger("autosar_hld_chunker")

class AUTOSARChunker:
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separators = separators or ["\n\n", "\n", ". ", "; ", " "]

    @staticmethod
    def format_table_as_markdown(table: TableData) -> str:
        """Convert a TableData object into a clean Markdown table representation."""
        if not table.rows:
            return ""

        rows = table.rows
        cleaned_rows = []
        for row in rows:
            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
            cleaned_rows.append(cleaned_row)

        if not cleaned_rows:
            return ""

        header = cleaned_rows[0]
        markdown_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |"
        ]

        for row in cleaned_rows[1:]:
            # Ensure row length matches header
            padded = row + [""] * (len(header) - len(row))
            markdown_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

        return "\n".join(markdown_lines)

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using hierarchy of separators until pieces fit chunk_size."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # Hard character cut if no separators remain
            pieces = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                pieces.append(text[i:i + self.chunk_size].strip())
            return [p for p in pieces if p]

        sep = separators[0]
        next_seps = separators[1:]

        if sep in text:
            splits = text.split(sep)
        else:
            return self._split_text_recursive(text, next_seps)

        # Merge splits up to chunk_size
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for s in splits:
            s_clean = s.strip()
            if not s_clean:
                continue

            add_len = len(s_clean) + (len(sep) if current_chunk else 0)
            if current_len + add_len <= self.chunk_size:
                current_chunk.append(s_clean)
                current_len += add_len
            else:
                if current_chunk:
                    merged = sep.join(current_chunk).strip()
                    if merged:
                        chunks.append(merged)
                # If individual element is larger than chunk_size, split recursively
                if len(s_clean) > self.chunk_size:
                    chunks.extend(self._split_text_recursive(s_clean, next_seps))
                    current_chunk = []
                    current_len = 0
                else:
                    current_chunk = [s_clean]
                    current_len = len(s_clean)

        if current_chunk:
            merged = sep.join(current_chunk).strip()
            if merged:
                chunks.append(merged)

        return chunks

    def split_text_with_overlap(self, text: str) -> List[str]:
        """Split text with configurable size and overlap between consecutive chunks."""
        raw_pieces = self._split_text_recursive(text, self.separators)
        if len(raw_pieces) <= 1:
            return raw_pieces

        # Apply overlap between consecutive pieces
        overlapped_chunks: List[str] = []
        for i, piece in enumerate(raw_pieces):
            if i == 0:
                overlapped_chunks.append(piece)
            else:
                prev_piece = raw_pieces[i - 1]
                # Extract overlap from end of previous piece on a word boundary
                overlap_text = prev_piece[-self.chunk_overlap:] if len(prev_piece) > self.chunk_overlap else prev_piece
                # Trim to complete word if possible
                word_break = overlap_text.find(" ")
                if word_break != -1 and word_break < len(overlap_text) - 5:
                    overlap_text = overlap_text[word_break + 1:]

                combined = f"{overlap_text} ... {piece}".strip()
                if len(combined) <= self.chunk_size * 1.2:
                    overlapped_chunks.append(combined)
                else:
                    overlapped_chunks.append(piece)

        return overlapped_chunks

    def partition_page_by_headings(
        self,
        page_text: str,
        headings: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Partition page text into (heading, text_block) pairs based on detected headings.
        If no headings or headings not found in text, returns [('General', page_text)].
        """
        if not page_text:
            return []

        if not headings:
            return [("General", page_text)]

        # Find heading positions in page text
        heading_positions: List[Tuple[int, str]] = []
        for h in headings:
            h_clean = h.strip()
            if not h_clean:
                continue
            idx = page_text.find(h_clean)
            if idx != -1:
                heading_positions.append((idx, h_clean))

        if not heading_positions:
            return [(headings[0] if headings else "General", page_text)]

        heading_positions.sort(key=lambda x: x[0])

        blocks: List[Tuple[str, str]] = []
        # Pre-heading text (if any)
        first_pos, first_heading = heading_positions[0]
        if first_pos > 0:
            pre_text = page_text[:first_pos].strip()
            if pre_text:
                blocks.append(("General", pre_text))

        for i, (pos, heading) in enumerate(heading_positions):
            start = pos + len(heading)
            end = heading_positions[i + 1][0] if i + 1 < len(heading_positions) else len(page_text)
            block_text = page_text[start:end].strip()
            full_section_text = f"{heading}\n\n{block_text}".strip() if block_text else heading
            blocks.append((heading, full_section_text))

        return blocks

    def create_chunks_from_page(
        self,
        page: DocumentPageResponse,
        doc_meta: Dict[str, Any],
        starting_chunk_index: int
    ) -> List[Chunk]:
        """
        Generate all context-aware chunks for a single processed page:
        1. Text/heading chunks (partitioned by section)
        2. Structured table chunks (markdown format with source_type='table')
        """
        chunks: List[Chunk] = []
        current_index = starting_chunk_index
        document_id = str(doc_meta.get("document_id", page.document_id))
        filename = str(doc_meta.get("filename", "unknown.pdf"))
        version_tag = str(doc_meta.get("version_tag", "v1.0"))
        page_number = int(page.page_number)
        is_ocr = bool(page.is_ocr)
        base_source_type = "ocr" if is_ocr else "text"

        # 1. Process Sectional Text
        section_blocks = self.partition_page_by_headings(page.cleaned_text, page.headings)

        for heading, block_text in section_blocks:
            if not block_text.strip():
                continue

            text_chunks = self.split_text_with_overlap(block_text)
            for txt in text_chunks:
                txt_clean = txt.strip()
                if not txt_clean:
                    continue

                chunk_id = f"{document_id}_p{page_number}_c{current_index}"
                word_count = len(txt_clean.split())
                char_count = len(txt_clean)

                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=current_index,
                    document_id=document_id,
                    filename=filename,
                    version_tag=version_tag,
                    page_number=page_number,
                    heading=heading,
                    source_type=base_source_type,
                    is_ocr=is_ocr,
                    word_count=word_count,
                    char_count=char_count
                )

                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    content=txt_clean,
                    metadata=metadata
                ))
                current_index += 1

        # 2. Process Tables as dedicated structured chunks
        if page.has_tables and page.tables:
            for t_idx, table in enumerate(page.tables):
                table_md = self.format_table_as_markdown(table)
                if not table_md.strip():
                    continue

                chunk_id = f"{document_id}_p{page_number}_c{current_index}"
                table_heading = page.headings[0] if page.headings else f"Table {t_idx + 1}"
                table_content = f"### [Table Data: Page {page_number}]\n{table_md}"
                word_count = len(table_content.split())
                char_count = len(table_content)

                table_meta = ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=current_index,
                    document_id=document_id,
                    filename=filename,
                    version_tag=version_tag,
                    page_number=page_number,
                    heading=table_heading,
                    source_type="table",
                    is_ocr=is_ocr,
                    word_count=word_count,
                    char_count=char_count
                )

                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    content=table_content,
                    metadata=table_meta
                ))
                current_index += 1

        return chunks

    def create_chunks_from_document(
        self,
        document_id: str,
        pages: List[DocumentPageResponse],
        doc_meta: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Process an entire document's pages in sequence into a continuous list of traceable chunks.
        """
        all_chunks: List[Chunk] = []
        global_chunk_idx = 0

        # Sort pages by page_number ASC for strict chronological integrity
        sorted_pages = sorted(pages, key=lambda p: p.page_number)

        for page in sorted_pages:
            page_chunks = self.create_chunks_from_page(
                page=page,
                doc_meta=doc_meta,
                starting_chunk_index=global_chunk_idx
            )
            all_chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)

        logger.info(
            f"Chunked document {document_id}: {len(sorted_pages)} pages -> {len(all_chunks)} chunks."
        )
        return all_chunks
