"use strict";

const path = require("path");
const { workspace } = require("vscode");
const {
  LanguageClient,
  TransportKind
} = require("vscode-languageclient/node");

let client;

function activate(context) {
  const extensionPath = context.extensionPath;
  const repoRoot = path.resolve(extensionPath, "..");
  const srcPath = path.join(repoRoot, "src");
  const env = Object.assign({}, process.env);
  env.PYTHONPATH = env.PYTHONPATH
    ? `${srcPath}${path.delimiter}${env.PYTHONPATH}`
    : srcPath;

  const serverOptions = {
    command: "python",
    args: ["-m", "psyker_lsp"],
    options: {
      cwd: repoRoot,
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
}

function deactivate() {
  if (!client) {
    return undefined;
  }
  return client.stop();
}

module.exports = {
  activate,
  deactivate
};
