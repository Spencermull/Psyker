"use strict";

const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
const { workspace, window, commands, Uri } = vscode;
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const env = buildServerEnvironment();
  const serverOptions = {
    command: "python",
    args: ["-m", "psyker_lsp"],
    options: {
      cwd: workspace.workspaceFolders?.[0]?.uri.fsPath,
      env
    },
    transport: TransportKind.stdio
  };

  const clientOptions = {
    documentSelector: [
      { scheme: "file", language: "psy" },
      { scheme: "file", language: "psya" },
      { scheme: "file", language: "psyw" }
    ],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.{psy,psya,psyw}")
    }
  };

  client = new LanguageClient(
    "psykerLanguageServer",
    "Psyker Language Server",
    serverOptions,
    clientOptions
  );

  context.subscriptions.push(client.start());
  context.subscriptions.push(
    commands.registerCommand("psyker.runTask", () => runTaskCommand(false)),
    commands.registerCommand("psyker.debugTask", () => runTaskCommand(true)),
    commands.registerCommand("psyker.addDebugConfiguration", addDebugConfigurationCommand)
  );
}

function deactivate() {
  if (!client) {
    return undefined;
  }
  return client.stop();
}

function buildServerEnvironment() {
  const env = Object.assign({}, process.env);
  const srcPaths = [];
  for (const folder of workspace.workspaceFolders || []) {
    const candidate = path.join(folder.uri.fsPath, "src");
    if (fs.existsSync(candidate)) {
      srcPaths.push(candidate);
    }
  }
  if (srcPaths.length > 0) {
    const existing = env.PYTHONPATH ? env.PYTHONPATH.split(path.delimiter) : [];
    env.PYTHONPATH = [...srcPaths, ...existing].join(path.delimiter);
  }
  return env;
}

async function runTaskCommand(debugMode) {
  const editor = window.activeTextEditor;
  if (!editor || editor.document.languageId !== "psy") {
    window.showErrorMessage("Psyker run/debug commands require an active .psy editor.");
    return;
  }

  const taskName = await resolveTaskName(editor.document, editor.selection.active.line);
  if (!taskName) {
    return;
  }

  const agentSelection = await resolveAgentSelection();
  if (!agentSelection) {
    return;
  }

  const configuration = workspace.getConfiguration("psyker");
  const cliPath = String(configuration.get("cliPath", "psyker")).trim() || "psyker";
  const sandboxRoot = String(configuration.get("sandboxRoot", "")).trim();
  const terminalEnv = sandboxRoot ? { PSYKER_SANDBOX_ROOT: sandboxRoot } : undefined;
  const terminal = window.createTerminal({
    name: debugMode ? "Psyker Debug" : "Psyker Run",
    env: terminalEnv
  });

  const workerFiles = await workspace.findFiles("**/*.psyw");
  const agentFiles = await workspace.findFiles("**/*.psya");
  const taskPath = editor.document.uri.fsPath;

  terminal.show(true);
  terminal.sendText(cliPath);
  for (const workerFile of workerFiles) {
    terminal.sendText(`load "${escapeForPsykerCli(workerFile.fsPath)}"`);
  }

  if (agentSelection.uri) {
    terminal.sendText(`load "${escapeForPsykerCli(agentSelection.uri.fsPath)}"`);
  } else {
    for (const agentFile of agentFiles) {
      terminal.sendText(`load "${escapeForPsykerCli(agentFile.fsPath)}"`);
    }
  }

  terminal.sendText(`load "${escapeForPsykerCli(taskPath)}"`);
  if (debugMode) {
    terminal.sendText(`stx agent ${agentSelection.name} --output json`);
    terminal.sendText(`stx task ${taskName} --output json`);
  }
  terminal.sendText(`run ${agentSelection.name} ${taskName}`);
}

async function addDebugConfigurationCommand() {
  const folder = workspace.workspaceFolders?.[0];
  if (!folder) {
    window.showErrorMessage("Open a workspace folder before adding Psyker debug configuration.");
    return;
  }

  const vscodeDir = Uri.file(path.join(folder.uri.fsPath, ".vscode"));
  await workspace.fs.createDirectory(vscodeDir);
  const launchUri = Uri.file(path.join(vscodeDir.fsPath, "launch.json"));
  const configName = "Psyker: Debug REPL";
  const newConfig = {
    name: configName,
    type: "python",
    request: "launch",
    module: "psyker",
    console: "integratedTerminal",
    cwd: "${workspaceFolder}",
    env: {
      PYTHONPATH: "${workspaceFolder}/src"
    }
  };

  let launchData = { version: "0.2.0", configurations: [] };
  try {
    const existing = await workspace.fs.readFile(launchUri);
    launchData = JSON.parse(Buffer.from(existing).toString("utf8"));
  } catch (_err) {
    // no launch.json yet
  }

  if (!Array.isArray(launchData.configurations)) {
    launchData.configurations = [];
  }
  if (!launchData.configurations.some((item) => item?.name === configName)) {
    launchData.configurations.push(newConfig);
  }

  await workspace.fs.writeFile(
    launchUri,
    Buffer.from(`${JSON.stringify(launchData, null, 2)}\n`, "utf8")
  );
  window.showInformationMessage("Added Psyker debug launch configuration to .vscode/launch.json");
}

async function resolveTaskName(document, cursorLine) {
  const tasks = extractTaskBlocks(document.getText());
  if (tasks.length === 0) {
    window.showErrorMessage("No task definitions found in this .psy file.");
    return null;
  }

  const inferred = tasks.find((item) => cursorLine >= item.startLine && cursorLine <= item.endLine);
  if (inferred) {
    return inferred.name;
  }
  if (tasks.length === 1) {
    return tasks[0].name;
  }

  const picked = await window.showQuickPick(
    tasks.map((item) => ({
      label: item.name,
      detail: `lines ${item.startLine + 1}-${item.endLine + 1}`
    })),
    {
      title: "Select task to run"
    }
  );
  return picked?.label || null;
}

async function resolveAgentSelection() {
  const config = workspace.getConfiguration("psyker");
  const defaultAgent = String(config.get("defaultAgent", "")).trim();
  const agentDefs = await collectAgentDefinitions();

  if (agentDefs.length === 0) {
    const manual = await window.showInputBox({
      title: "Agent name",
      prompt: "No .psya agent files were found. Enter an agent name to run.",
      value: defaultAgent
    });
    if (!manual) {
      return null;
    }
    return { name: manual.trim(), uri: undefined };
  }

  const sortedDefs = [...agentDefs].sort((a, b) => a.name.localeCompare(b.name));
  const preferred = sortedDefs.find((item) => item.name === defaultAgent);
  if (preferred) {
    return preferred;
  }
  if (sortedDefs.length === 1) {
    return sortedDefs[0];
  }

  const picked = await window.showQuickPick(
    sortedDefs.map((item) => ({
      label: item.name,
      detail: workspace.asRelativePath(item.uri, false),
      item
    })),
    {
      title: "Select agent to run task with"
    }
  );
  return picked?.item || null;
}

async function collectAgentDefinitions() {
  const uris = await workspace.findFiles("**/*.psya");
  const definitions = [];
  const pattern = /^\s*agent\s+([A-Za-z][A-Za-z0-9_-]*)\b/gm;
  for (const uri of uris) {
    let text;
    try {
      const bytes = await workspace.fs.readFile(uri);
      text = Buffer.from(bytes).toString("utf8");
    } catch (_err) {
      continue;
    }
    let match = pattern.exec(text);
    while (match) {
      definitions.push({ name: match[1], uri });
      match = pattern.exec(text);
    }
    pattern.lastIndex = 0;
  }
  return definitions;
}

function extractTaskBlocks(text) {
  const lines = text.split(/\r?\n/);
  const blocks = [];
  const taskPattern = /^\s*task\s+([A-Za-z][A-Za-z0-9_-]*)\b.*\{/;
  for (let i = 0; i < lines.length; i += 1) {
    const match = taskPattern.exec(lines[i]);
    if (!match) {
      continue;
    }
    let depth = 0;
    let started = false;
    let endLine = i;
    for (let j = i; j < lines.length; j += 1) {
      for (const char of lines[j]) {
        if (char === "{") {
          depth += 1;
          started = true;
        } else if (char === "}") {
          depth -= 1;
          if (started && depth <= 0) {
            endLine = j;
            break;
          }
        }
      }
      if (started && depth <= 0) {
        break;
      }
    }
    blocks.push({ name: match[1], startLine: i, endLine });
  }
  return blocks;
}

function escapeForPsykerCli(value) {
  return value.replace(/"/g, '\\"');
}

module.exports = {
  activate,
  deactivate
};
