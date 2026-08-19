#!/usr/bin/env python3

import argparse
import csv
import os
import re
from multiprocessing import Pool


# ============================================================
# Interpreter definitions
# ============================================================

PYTHON_RE = r"(?:python(?:\d+(?:\.\d+)*)?|pypy(?:\d+)?)"

SHELL_RE = r"(?:bash|sh|zsh|dash|ksh)"

SCRIPT_E_RE = r"(?:node|nodejs|perl|ruby)"

ALL_INTERPRETERS_RE = (
    rf"(?:"
    rf"{PYTHON_RE}"
    rf"|{SHELL_RE}"
    rf"|{SCRIPT_E_RE}"
    rf"|php"
    rf")"
)


# ============================================================
# Regex patterns
# ============================================================

#
# 前面只要求不是普通字母/数字/下划线。
#
# 因此以下都可以识别：
#
#   python
#   ;python
#   &&python
#   |python
#   >python
#   "python
#   'python
#   \npython
#
# 但不会把：
#
#   mypython
#   cpython
#
# 当成 python。
#

PREFIX = r"(?<![A-Za-z0-9_])"

# 可选绝对路径：
# /usr/bin/python3
# /usr/local/bin/bash
PATH_PREFIX = r"(?:[A-Za-z0-9_.+\-/]+/)?"


PATTERNS = (

    # ========================================================
    # 1. Python / PyPy -c
    #
    # python -c "..."
    # python3 -c "..."
    # python3 -u -c "..."
    # /usr/bin/python3 -c "..."
    # cd /tmp &&python -c "..."
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {PYTHON_RE}
        \b

        (?:
            [ \t]+
            -[A-Za-z]+
        )*

        [ \t]*
        -c

        (?=
            [ \t\r\n]
            |
            ["']
            |
            \\
            |
            $
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 2. bash/sh/zsh/... -c
    #
    # bash -c "..."
    # sh -c "..."
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {SHELL_RE}
        \b

        (?:
            [ \t]+
            -[A-Za-z]+
        )*

        [ \t]*
        -c

        (?=
            [ \t\r\n]
            |
            ["']
            |
            \\
            |
            $
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 3. node/perl/ruby -e
    #
    # node -e "..."
    # perl -e "..."
    # ruby -e "..."
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {SCRIPT_E_RE}
        \b

        (?:
            [ \t]+
            -[A-Za-z]+
        )*

        [ \t]*
        -e

        (?=
            [ \t\r\n]
            |
            ["']
            |
            \\
            |
            $
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 4. PHP -r
    #
    # php -r 'echo "xxx";'
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        php
        \b
        [ \t]*
        -r

        (?=
            [ \t\r\n]
            |
            ["']
            |
            \\
            |
            $
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 5. Interpreter + heredoc
    #
    # python <<EOF
    #
    # python <<'PY'
    #
    # python3 - <<PY
    #
    # bash <<EOF
    #
    # xxx && python3 - <<'PY'
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {ALL_INTERPRETERS_RE}
        \b

        [^;&|]{{0,300}}?

        <<-?
        [ \t]*
        ['"]?
        [A-Za-z_][A-Za-z0-9_]*
        ['"]?
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 6. Heredoc pipe 到解释器
    #
    # cat <<EOF | python
    #
    # cat <<'PY' | python3
    # ========================================================
    re.compile(
        rf"""
        <<-?
        [ \t]*
        ['"]?
        [A-Za-z_][A-Za-z0-9_]*
        ['"]?

        [\s\S]*?

        \|

        [ \t]*

        {PATH_PREFIX}
        {ALL_INTERPRETERS_RE}
        \b
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 7. 非法/污染形式：
    #
    # python"""xxx"""
    #
    # python'''xxx'''
    #
    # python """xxx"""
    #
    # python3'''xxx'''
    #
    # xxx\npython"""xxx"""\nprint(...)
    #
    # 这种一般是源码错误地混入 source 字段。
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {PYTHON_RE}
        \b

        [ \t]*

        (?:
            "{{3}}
            |
            '{{3}}
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
)


# ============================================================
# Source normalization
# ============================================================

def normalize_source(source: str) -> str:
    """
    仅在内存中用于检测。

    不修改最终输出的 source 内容。

    很多 TSV 数据可能保存的是字面字符串：

        abc\\npython -c "xxx"

    而不是实际换行。

    临时转为：

        abc
        python -c "xxx"

    再进行检测。
    """

    if not source:
        return ""

    source = str(source)

    # 注意顺序，先处理 \r\n
    source = source.replace(r"\r\n", "\n")
    source = source.replace(r"\n", "\n")
    source = source.replace(r"\r", "\n")
    source = source.replace(r"\t", " ")

    return source


# ============================================================
# Detection
# ============================================================

def contains_inline_source(source: str) -> bool:
    """
    返回 True:
        source 包含内嵌代码、heredoc 或明显源码污染，
        删除整条记录。

    返回 False:
        保留。
    """

    if not source:
        return False

    cmd = normalize_source(source)

    for pattern in PATTERNS:
        if pattern.search(cmd):
            return True

    return False


# ============================================================
# Multiprocessing
# ============================================================

def process_chunk(rows):
    """
    一个 worker 一次处理一批数据。
    """

    kept_rows = []
    removed = 0

    for row in rows:
        source = row.get("source", "") or ""

        if contains_inline_source(source):
            removed += 1
        else:
            kept_rows.append(row)

    return kept_rows, removed, len(rows)


def read_chunks(reader, chunk_size):
    """
    流式读取，避免一次把整个 TSV 放进内存。
    """

    chunk = []

    for row in reader:
        chunk.append(row)

        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


# ============================================================
# Cleaning
# ============================================================

def clean_tsv(
    input_file: str,
    output_file: str,
    workers: int,
    chunk_size: int,
):
    total = 0
    kept = 0
    removed = 0

    with open(
        input_file,
        "r",
        encoding="utf-8",
        newline="",
        buffering=1024 * 1024,
    ) as fin:

        reader = csv.DictReader(
            fin,
            delimiter="\t",
        )

        if not reader.fieldnames:
            raise ValueError("TSV 文件没有表头")

        if "source" not in reader.fieldnames:
            raise ValueError(
                "TSV 中不存在 source 字段。\n"
                f"当前字段：{reader.fieldnames}"
            )

        with open(
            output_file,
            "w",
            encoding="utf-8",
            newline="",
            buffering=1024 * 1024,
        ) as fout:

            writer = csv.DictWriter(
                fout,
                fieldnames=reader.fieldnames,
                delimiter="\t",
                quoting=csv.QUOTE_MINIMAL,
            )

            writer.writeheader()

            chunks = read_chunks(
                reader,
                chunk_size,
            )

            # 单核时直接执行，避免 multiprocessing 开销
            if workers == 1:

                for chunk in chunks:

                    kept_rows, removed_count, chunk_total = (
                        process_chunk(chunk)
                    )

                    writer.writerows(kept_rows)

                    total += chunk_total
                    kept += len(kept_rows)
                    removed += removed_count

                    if total % 100000 < chunk_size:
                        print(
                            f"\r已处理 {total:,} 条 | "
                            f"保留 {kept:,} | "
                            f"过滤 {removed:,}",
                            end="",
                            flush=True,
                        )

            else:

                with Pool(processes=workers) as pool:

                    # imap 保证输出顺序和原始 TSV 一致
                    for (
                        kept_rows,
                        removed_count,
                        chunk_total,
                    ) in pool.imap(
                        process_chunk,
                        chunks,
                        chunksize=1,
                    ):

                        writer.writerows(kept_rows)

                        total += chunk_total
                        kept += len(kept_rows)
                        removed += removed_count

                        if total % 100000 < chunk_size:
                            print(
                                f"\r已处理 {total:,} 条 | "
                                f"保留 {kept:,} | "
                                f"过滤 {removed:,}",
                                end="",
                                flush=True,
                            )

    print()

    print("=" * 60)
    print(f"总记录数:   {total:,}")
    print(f"保留记录数: {kept:,}")
    print(f"过滤记录数: {removed:,}")

    if total > 0:
        print(f"过滤比例:   {removed / total:.2%}")

    print(f"CPU进程数:  {workers}")
    print(f"Chunk大小:  {chunk_size:,}")
    print(f"输出文件:   {output_file}")


# ============================================================
# CLI
# ============================================================

def main():

    cpu_count = os.cpu_count() or 1

    default_workers = max(
        1,
        cpu_count - 1,
    )

    parser = argparse.ArgumentParser(
        description=(
            "过滤 TSV source 字段中的内嵌源码、"
            "heredoc 和明显源码污染数据。"
            "普通脚本文件执行如 python test.py 会保留。"
        )
    )

    parser.add_argument(
        "input",
        help="输入 TSV 文件",
    )

    parser.add_argument(
        "output",
        help="输出 TSV 文件",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=default_workers,
        help=(
            f"并行进程数，默认 CPU 数 - 1。"
            f"当前默认值：{default_workers}"
        ),
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="每个并行任务处理的数据条数，默认 5000",
    )

    args = parser.parse_args()

    if args.workers < 1:
        raise ValueError("--workers 必须 >= 1")

    if args.chunk_size < 1:
        raise ValueError("--chunk-size 必须 >= 1")

    clean_tsv(
        input_file=args.input,
        output_file=args.output,
        workers=args.workers,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
