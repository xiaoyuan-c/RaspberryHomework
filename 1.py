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

# python 前面允许：
# 空格、&&、;、|、>、引号、换行等等
#
# 但防止：
# mypython
# abc_python
#
# 中间的 python 被错误命中
PREFIX = r"(?<![A-Za-z0-9_])"

# 支持：
# /usr/bin/python3
# /usr/local/bin/python
PATH_PREFIX = r"(?:[A-Za-z0-9_.+\-/]+/)?"


# ============================================================
# Patterns
# ============================================================

PATTERNS = (

    # ========================================================
    # 1. python -c
    #
    # python -c "..."
    # python3 -c "..."
    # python3 -u -c "..."
    # cd xxx && python -c "..."
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
    # 2. shell -c
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
    # 4. php -r
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
    # 5. interpreter + heredoc
    #
    # python <<EOF
    # python3 - <<'PY'
    # bash <<EOF
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
    # 6. heredoc | interpreter
    #
    # cat <<EOF | python
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
    # 7. Python + triple quote
    #
    # python"""xxx"""
    # python'''xxx'''
    # python3"""xxx"""
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


    # ========================================================
    # 8. 【新增】python 后面直接粘源码/异常文本
    #
    # pythonxxx
    # pythonprint(...)
    # pythonimport
    # python"""xxx"""
    # python'xxx'
    # python("xxx")
    #
    # 也支持：
    # cd xxx && pythonxxx
    # xxx;pythonimport
    #
    # 正常版本号不会误杀：
    # python3
    # python3.11
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {PYTHON_RE}

        (?=
            [A-Za-z_]
            |
            ["']
            |
            \(
            |
            \[
            |
            \{{
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    ),


    # ========================================================
    # 9. 【新增】Python 解释器后直接换行
    #
    # python\nxxxx
    #
    # python3\nimport os
    #
    # cd xxx && python\nprint(...)
    #
    # TSV 中的字面量 \n 会先被转换成真正换行。
    #
    # 这种通常表示：
    # Python 源码被错误拼接进 source。
    # ========================================================
    re.compile(
        rf"""
        {PREFIX}
        {PATH_PREFIX}
        {PYTHON_RE}
        \b
        [ \t]*
        \r?\n
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
)


# ============================================================
# Normalize source
# ============================================================

def normalize_source(source: str) -> str:
    """
    仅在内存中规范化 source，用于检测。

    不会修改最终 TSV 中的数据。

    例如 TSV 中实际存储：

        cd /tmp\\npython -c "xxx"

    转换为：

        cd /tmp
        python -c "xxx"
    """

    if not source:
        return ""

    source = str(source)

    # 顺序很重要
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
    True:
        删除该记录。

    False:
        保留该记录。
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

    chunk = []

    for row in reader:

        chunk.append(row)

        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


# ============================================================
# TSV cleaning
# ============================================================

def clean_tsv(
    input_file,
    output_file,
    workers,
    chunk_size,
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
                f"TSV 中不存在 source 字段，当前字段："
                f"{reader.fieldnames}"
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

            # =================================================
            # 单进程
            # =================================================

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

            # =================================================
            # 多进程
            # =================================================

            else:

                with Pool(processes=workers) as pool:

                    # imap 保证输出顺序不变
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

    if total:
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
            "过滤 TSV source 中的内嵌源码、heredoc、"
            "非法 Python 调用及源码污染数据"
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
        help=f"CPU 并行进程数，默认 {default_workers}",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="每批数据量，默认 5000",
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
