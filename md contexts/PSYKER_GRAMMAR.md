# PSYKER v0.1 — Formal Grammar (EBNF)

> **Examples Notice**
>
> All code snippets in this documentation are **illustrative examples** of valid syntax.
> Implementations MUST follow **PSYKER_GRAMMAR.md** and MUST NOT hardcode behavior based on example patterns,
> fixed statement ordering, or specific example file layouts.


This document defines the **formal grammar** for PSYKER v0.1 across the three file dialects:

- `.psy`  → **Task dialect** (task code)
- `.psya` → **Agent dialect** (agent definitions)
- `.psyw` → **Worker dialect** (worker definitions)

The interpreter MUST select the dialect **by file extension** and reject cross-dialect constructs as errors.

---

## 1) Lexical Tokens (Shared)

**Whitespace**
- Whitespace separates tokens: space, tab, CR, LF.
- Newlines have no semantic meaning except for diagnostics.
- Comments start with `#` and run to end-of-line.

**Identifiers**
- Used for names: workers, agents, tasks.
- Recommended: `[A-Za-z][A-Za-z0-9_-]*`

**Integers**
- Used for counts: `[0-9]+`

**Strings**
- Double-quoted with backslash escapes.
- Used for commands and paths with spaces.

**Paths**
- Either a quoted STRING or a bare path token.
- Bare paths should support: `A-Z a-z 0-9 _ - . / \ :`

---

## 2) EBNF (Lexical-Level)

```ebnf
letter      = "A"…"Z" | "a"…"z" ;
digit       = "0"…"9" ;
ws          = " " | "\t" | "\r" | "\n" ;

IDENT       = letter , { letter | digit | "_" | "-" } ;
INT         = digit , { digit } ;

STRING      = '"' , { string_char } , '"' ;
string_char = ? any char except " and newline ? | '\"' ;

BARE_PATH   = (letter | digit | "_" | "-" | "." | "/" | "\\" | ":" ) ,
              { letter | digit | "_" | "-" | "." | "/" | "\\" | ":" } ;

PATH        = STRING | BARE_PATH ;

COMMENT     = "#" , { ? any char except newline ? } ;
```

---

## 3) Dialect Dispatch (Hard Rule)

```text
if file endswith .psy  → parse using Task grammar
if file endswith .psya → parse using Agent grammar
if file endswith .psyw → parse using Worker grammar
otherwise              → error
```

A file parsed under the wrong dialect MUST produce a **DialectError** with line/column.

---

## 4) Task Dialect Grammar (`.psy`)

### 4.1 Structure

```ebnf
psy_file      = { ws | COMMENT } , { task_def , { ws | COMMENT } } ;

task_def      = [ access_block ] ,
                "task" , ws+ , task_name , ws* , "{" , ws* ,
                  { task_stmt , { ws | COMMENT } } ,
                "}" , ws* ;

task_name     = IDENT ;

access_block  = "@access" , ws* , "{" , ws* ,
                  [ "agents" , ws* , ":" , ws* , ident_list , ws* ] ,
                  [ "," , ws* , "workers" , ws* , ":" , ws* , ident_list , ws* ] ,
                "}" , ws* ;

ident_list    = "[" , ws* , [ IDENT , { ws* , "," , ws* , IDENT } ] , ws* , "]" ;
```

### 4.2 Task Statements (v0.1)

v0.1 tasks may only contain these statements. Each statement MUST end with `;`.

```ebnf
task_stmt      = fs_open_stmt
               | fs_create_stmt
               | exec_ps_stmt
               | exec_cmd_stmt ;

fs_open_stmt   = "fs.open" , ws+ , PATH , ws* , ";" ;
fs_create_stmt = "fs.create" , ws+ , PATH , ws* , ";" ;

exec_ps_stmt   = "exec.ps" , ws+ , STRING , ws* , ";" ;
exec_cmd_stmt  = "exec.cmd" , ws+ , STRING , ws* , ";" ;
```

---

## 5) Worker Dialect Grammar (`.psyw`)

```ebnf
psyw_file     = { ws | COMMENT } , worker_def , { ws | COMMENT } ;

worker_def    = "worker" , ws+ , worker_name , ws* , "{" , ws* ,
                  { worker_stmt , { ws | COMMENT } } ,
                "}" , ws* ;

worker_name   = IDENT ;

worker_stmt   = allow_stmt
              | sandbox_stmt
              | cwd_stmt ;

allow_stmt    = "allow" , ws+ , capability , [ ws+ , capability_arg ] , ws* , ";" ;

capability    = "fs.open"
              | "fs.create"
              | "exec.ps"
              | "exec.cmd" ;

capability_arg= PATH | STRING ;

sandbox_stmt  = "sandbox" , ws+ , PATH , ws* , ";" ;
cwd_stmt      = "cwd" , ws+ , PATH , ws* , ";" ;
```

---

## 6) Agent Dialect Grammar (`.psya`)

```ebnf
psya_file      = { ws | COMMENT } , agent_def , { ws | COMMENT } ;

agent_def      = "agent" , ws+ , agent_name , ws* , "{" , ws* ,
                   { agent_stmt , { ws | COMMENT } } ,
                 "}" , ws* ;

agent_name     = IDENT ;

agent_stmt     = use_worker_stmt ;

use_worker_stmt
              = "use" , ws+ , "worker" , ws+ , worker_name ,
                ws+ , "count" , ws* , "=" , ws* , INT , ws* , ";" ;
```

---

## 7) Reserved Words (v0.1)

```text
Task (.psy):   task, @access, agents, workers, fs.open, fs.create, exec.ps, exec.cmd
Worker (.psyw):worker, allow, sandbox, cwd, fs.open, fs.create, exec.ps, exec.cmd
Agent (.psya): agent, use, worker, count
```

A dialect MUST reject reserved words from other dialects as **DialectError**.

## Modular Extensibility

- Grammar is versioned; `v0.x` is additive-only.
- New statements/capabilities must be feature-flagged until promoted.
- Dialect boundaries are stable extension points; cross-dialect constructs are DialectError.

## REPL vs File Grammar

The interactive CLI may be bash-like, but `.psy/.psya/.psyw` file syntax is governed strictly by this EBNF.
