import re


# ============================================================
# Interpreter
# ============================================================

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


# ============================================================
# Normalize
# ============================================================

def normalize_command(command: str) -> str:
    """
    只为了检测做规范化，不修改最终输出数据。

    将 TSV 中保留下来的字面量转义符：
        \\n
        \\r
        \\t

    转为空白，从而避免：
        cd /tmp\\npython -c "xxx"

    这种情况漏检。
    """
    if not command:
        return ""

    cmd = command

    # 字面量 \n
    cmd = cmd.replace(r"\n", "\n")

    # 字面量 \r
    cmd = cmd.replace(r"\r", "\n")

    # 字面量 \t
    cmd = cmd.replace(r"\t", " ")

    return cmd


# ============================================================
# Regex
# ============================================================

# 不再规定 python 前面必须是空格、;、& 等。
#
# 只要求 python 前面不能直接是：
# 字母 / 数字 / 下划线
#
# 因此：
#   "python
#   'python
#   ;python
#   &&python
#   |python
#   >python
#   \npython
#   (python
#
# 都能识别。
#
# 但：
#   mypython
#   cpython
#
# 不会错误匹配。

PYTHON_C_RE = re.compile(
    rf"""
    (?<![A-Za-z0-9_])
    (?:[A-Za-z0-9_.+\-/]+/)?        # 可选路径 /usr/bin/
    (?:python(?:\d+(?:\.\d+)*)?|pypy(?:\d+)?)\b
    (?:
        \s+
        -[A-Za-z]+                  # 例如 -u -B
    )*
    \s*
    -c
    (?=\s|["'\\]|$)
    """,
    re.IGNORECASE | re.VERBOSE,
)


SHELL_C_RE = re.compile(
    rf"""
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
)


SCRIPT_E_RE = re.compile(
    rf"""
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
)


PHP_R_RE = re.compile(
    r"""
    (?<![A-Za-z0-9_])
    (?:[A-Za-z0-9_.+\-/]+/)?
    php\b
    \s*
    -r
    (?=\s|["'\\]|$)
    """,
    re.IGNORECASE | re.VERBOSE,
)


# python <<EOF
# python3 - <<'PY'
# bash << EOF
HEREDOC_INTERPRETER_RE = re.compile(
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
)


# cat <<EOF | python3
HEREDOC_PIPE_RE = re.compile(
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
)


PATTERNS = (
    PYTHON_C_RE,
    SHELL_C_RE,
    SCRIPT_E_RE,
    PHP_R_RE,
    HEREDOC_INTERPRETER_RE,
    HEREDOC_PIPE_RE,
)


def contains_inline_source(command: str) -> bool:
    if not command:
        return False

    cmd = normalize_command(command)

    for pattern in PATTERNS:
        if pattern.search(cmd):
            return True

    return False
