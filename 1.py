#!/usr/bin/env python3

import argparse
import csv
import re


# 常见的解释器/脚本运行器
INTERPRETERS = (
    r"python(?:\d+(?:\.\d+)*)?",
    r"pypy(?:\d+)?",
    r"bash",
    r"sh",
    r"zsh",
    r"dash",
    r"ksh",
    r"node",
    r"nodejs",
    r"perl",
    r"ruby",
    r"php",
)

INTERPRETER_RE = r"(?:" + "|".join(INTERPRETERS) + r")"

# 允许解释器以绝对路径出现，例如 /usr/bin/python3
EXEC_RE = rf"(?:^|[\s;&|()])(?:[^\s;&|()]*/)?{INTERPRETER_RE}\b"


def contains_inline_source(command: str) -> bool:
    """
    判断命令中是否包含直接嵌入的源码。

    返回 True  -> 应过滤
    返回 False -> 保留
    """

    if not command:
        return False

    cmd = command.strip()

    # ---------------------------------------------------------
    # 1. python/bash/sh 等通过 -c 执行源码
    #
    # python -c "print(1)"
    # python3 -c '...'
    # bash -c "rm ..."
    # sh -c '...'
    # ---------------------------------------------------------
    pattern_c = rf"""
        {EXEC_RE}
        \s+
        (?:-[A-Za-z]*\s+)*      # 允许前面存在部分选项
        -c
        (?:\s|["'])
    """

    if re.search(pattern_c, cmd, re.IGNORECASE | re.VERBOSE):
        return True

    # 更直接地处理紧贴引号的形式：
    # python3 -c"print(1)"
    pattern_c_compact = rf"""
        {EXEC_RE}
        \s+
        -c
        ["']
    """

    if re.search(pattern_c_compact, cmd, re.IGNORECASE | re.VERBOSE):
        return True

    # ---------------------------------------------------------
    # 2. perl/ruby/node 等常用 -e 表示直接执行代码
    #
    # perl -e 'print "hello"'
    # ruby -e 'puts 1'
    # node -e 'console.log(1)'
    # ---------------------------------------------------------
    pattern_e = rf"""
        (?:^|[\s;&|()])
        (?:[^\s;&|()]*/)?
        (?:perl|ruby|node|nodejs)\b
        \s+
        (?:-[A-Za-z]*\s+)*
        -e
        (?:\s|["'])
    """

    if re.search(pattern_e, cmd, re.IGNORECASE | re.VERBOSE):
        return True

    # ---------------------------------------------------------
    # 3. PHP -r 直接执行 PHP 源码
    #
    # php -r 'echo "hello";'
    # ---------------------------------------------------------
    pattern_php_r = r"""
        (?:^|[\s;&|()])
        (?:[^\s;&|()]*/)?
        php\b
        \s+
        -r
        (?:\s|["'])
    """

    if re.search(pattern_php_r, cmd, re.IGNORECASE | re.VERBOSE):
        return True

    # ---------------------------------------------------------
    # 4. 解释器 + heredoc
    #
    # python <<EOF
    # python3 <<'PY'
    # python3 - <<PY
    # bash <<EOF
    # ---------------------------------------------------------
    pattern_heredoc = rf"""
        {EXEC_RE}
        [^\n;&|]{{0,200}}?
        <<-?
        \s*
        ['"]?
        [A-Za-z_][A-Za-z0-9_]*
        ['"]?
    """

    if re.search(pattern_heredoc, cmd, re.IGNORECASE | re.VERBOSE):
        return True

    # ---------------------------------------------------------
    # 5. heredoc 通过管道输入解释器
    #
    # cat <<EOF | python
    # ...
    # EOF
    #
    # cat <<'PY' | python3
    # ---------------------------------------------------------
    heredoc_pipe_interpreter = rf"""
        <<-?
        \s*
        ['"]?
        [A-Za-z_][A-Za-z0-9_]*
        ['"]?
        [\s\S]*?
        \|
        \s*
        (?:[^\s;&|()]*/)?
        {INTERPRETER_RE}\b
    """

    if re.search(
        heredoc_pipe_interpreter,
        cmd,
        re.IGNORECASE | re.VERBOSE,
    ):
        return True

    return False


def clean_tsv(input_file: str, output_file: str):
    total = 0
    removed = 0
    kept = 0

    with open(input_file, "r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin, delimiter="\t")

        if not reader.fieldnames:
            raise ValueError("TSV 文件没有表头")

        if "source" not in reader.fieldnames:
            raise ValueError(
                f"TSV 中不存在 source 字段，当前字段：{reader.fieldnames}"
            )

        with open(output_file, "w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(
                fout,
                fieldnames=reader.fieldnames,
                delimiter="\t",
                quoting=csv.QUOTE_MINIMAL,
            )

            writer.writeheader()

            for row in reader:
                total += 1

                source = row.get("source", "") or ""

                if contains_inline_source(source):
                    removed += 1
                    continue

                writer.writerow(row)
                kept += 1

    print(f"总记录数: {total}")
    print(f"过滤记录数: {removed}")
    print(f"保留记录数: {kept}")
    print(f"过滤比例: {removed / total:.2%}" if total else "过滤比例: 0%")
    print(f"输出文件: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="过滤 TSV 中 source 字段包含内嵌源码的 Linux 命令"
    )

    parser.add_argument(
        "input",
        help="输入 TSV 文件",
    )

    parser.add_argument(
        "output",
        help="输出 TSV 文件",
    )

    args = parser.parse_args()

    clean_tsv(args.input, args.output)


if __name__ == "__main__":
    main()
