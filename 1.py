#!/usr/bin/env python3

import argparse
import csv
import os
import re
from multiprocessing import Pool


# ============================================================
# 需要识别的解释器
# ============================================================

INTERPRETER_RE = (
    r"(?:"
    r"python(?:\d+(?:\.\d+)*)?"
    r"|pypy(?:\d+)?"
    r"|bash"
    r"|sh"
    r"|zsh"
    r"|dash"
    r"|ksh"
    r"|node"
    r"|nodejs"
    r"|perl"
    r"|ruby"
    r"|php"
    r")"
)

PATTERNS = None


# ============================================================
# 每个 CPU worker 初始化一次正则
# ============================================================

def init_worker():
    global PATTERNS

    PATTERNS = (

        # ----------------------------------------------------
        # python / pypy -c
        #
        # python -c "xxx"
        # python3 -c "xxx"
        # python3 -u -c "xxx"
        # /usr/bin/python3 -c "xxx"
        # xxx&&python -c "xxx"
        # "python -c \"xxx\""
        # ----------------------------------------------------
        re.compile(
            r"""
            (?<![A-Za-z0-9_])
            (?:[A-Za-z0-9_.+\-/]+/)?
            (?:python(?:\d+(?:\.\d+)*)?|pypy(?:\d+)?)\b
            (?:
                \s+
                -[A-Za-z]+
            )*
            \s*
            -c
            (?=\s|["'\\]|$)
            """,
            re.IGNORECASE | re.VERBOSE,
        ),

        # ----------------------------------------------------
        # shell -c
        #
        # bash -c "xxx"
        # sh -c "xxx"
        # zsh -c "xxx"
        # ----------------------------------------------------
        re.compile(
            r"""
            (?<![A-Za-z0-9_])
            (?:[A-Za-z0-9_.+\-/]+/)?
            (?:bash|sh|zsh|dash|ksh)\b
            (?:
                \s+
                -[A-Za-z]+
            )*
            \s*
            -c
            (?=\s|["'\\]|$)
            """,
            re.IGNORECASE | re.VERBOSE,
        ),

        # ----------------------------------------------------
        # node / perl / ruby -e
        # ----------------------------------------------------
        re.compile(
            r"""
            (?<![A-Za-z0-9_])
            (?:[A-Za-z0-9_.+\-/]+/)?
            (?:node|nodejs|perl|ruby)\b
            (?:
                \s+
                -[A-Za-z]+
            )*
            \s*
            -e
            (?=\s|["'\\]|$)
            """,
            re.IGNORECASE | re.VERBOSE,
        ),

        # ----------------------------------------------------
        # php -r
        # ----------------------------------------------------
        re.compile(
            r"""
            (?<![A-Za-z0-9_])
            (?:[A-Za-z0-9_.+\-/]+/)?
            php\b
            \s*
            -r
            (?=\s|["'\\]|$)
            """,
            re.IGNORECASE | re.VERBOSE,
        ),

        # ----------------------------------------------------
        # 解释器 + heredoc
        #
        # python <<EOF
        # python3 <<'PY'
        # python3 - <<PY
        # bash <<EOF
        # ----------------------------------------------------
        re.compile(
            rf"""
            (?<![A-Za-z0-9_])
            (?:[A-Za-z0-9_.+\-/]+/)?
            {INTERPRETER_RE}\b

            [^;&|]{{0,300}}?

            <<-?
            \s*
            ['"]?
            [A-Za-z_][A-Za-z0-9_]*
            ['"]?
            """,
            re.IGNORECASE | re.VERBOSE,
        ),

        # ----------------------------------------------------
        # heredoc | interpreter
        #
        # cat <<EOF | python
        # cat <<'PY' | python3
        # ----------------------------------------------------
        re.compile(
            rf"""
            <<-?
            \s*
            ['"]?
            [A-Za-z_][A-Za-z0-9_]*
            ['"]?

            [\s\S]*?

            \|

            \s*

            (?:[A-Za-z0-9_.+\-/]+/)?
            {INTERPRETER_RE}\b
            """,
            re.IGNORECASE | re.VERBOSE,
        ),
    )


# ============================================================
# 判断一条 source 是否包含内嵌源码
# ============================================================

def contains_inline_source(source: str) -> bool:
    if not source:
        return False

    # --------------------------------------------------------
    # 这里只是在内存里临时转换。
    # 不修改原 TSV，也不会产生任何中间文件。
    #
    # TSV 可能存的是：
    #
    #   cd /tmp\npython -c "xxx"
    #
    # 实际字符串是：
    #
    #   cd /tmp\\npython -c "xxx"
    #
    # 转换后再进行检测。
    # --------------------------------------------------------

    cmd = source

    cmd = cmd.replace(r"\r\n", "\n")
    cmd = cmd.replace(r"\n", "\n")
    cmd = cmd.replace(r"\r", "\n")
    cmd = cmd.replace(r"\t", " ")

    for pattern in PATTERNS:
        if pattern.search(cmd):
            return True

    return False


# ============================================================
# 单个 CPU 处理一批数据
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


# ============================================================
# 流式读取
# ============================================================

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
# 主清洗函数
# ============================================================

def clean_tsv(input_file, output_file, workers, chunk_size):
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

        reader = csv.DictReader(fin, delimiter="\t")

        if not reader.fieldnames:
            raise ValueError("TSV 文件没有表头")

        if "source" not in reader.fieldnames:
            raise ValueError(
                f"找不到 source 字段，当前字段：{reader.fieldnames}"
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

            with Pool(
                processes=workers,
                initializer=init_worker,
            ) as pool:

                chunks = read_chunks(reader, chunk_size)

                for kept_rows, removed_count, chunk_total in pool.imap(
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
    print(f"总数据:   {total:,}")
    print(f"保留:     {kept:,}")
    print(f"过滤:     {removed:,}")

    if total:
        print(f"过滤比例: {removed / total:.2%}")

    print(f"CPU进程:  {workers}")
    print(f"输出文件: {output_file}")


# ============================================================
# CLI
# ============================================================

def main():
    cpu_count = os.cpu_count() or 1

    parser = argparse.ArgumentParser(
        description="过滤 TSV 中 source 字段包含内嵌源码的命令"
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
        default=max(1, cpu_count - 1),
        help=f"CPU进程数，默认 {max(1, cpu_count - 1)}",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="每个进程每批处理的数据量，默认 5000",
    )

    args = parser.parse_args()

    clean_tsv(
        input_file=args.input,
        output_file=args.output,
        workers=args.workers,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
