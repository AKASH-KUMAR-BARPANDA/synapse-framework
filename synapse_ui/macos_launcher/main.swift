import Cocoa
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate, WKUIDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var uiServerProcess: Process?
    var backendServerProcess: Process?
    var ollamaServerProcess: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        startOllamaDaemonIfNeeded()
        startFastApiBackendIfNeeded()
        startEmbeddedWebServer()

        let screenRect = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1280, height: 820)
        let width: CGFloat = min(1280, screenRect.width * 0.88)
        let height: CGFloat = min(820, screenRect.height * 0.88)
        let originX = screenRect.origin.x + (screenRect.width - width) / 2
        let originY = screenRect.origin.y + (screenRect.height - height) / 2

        let windowRect = NSRect(x: originX, y: originY, width: width, height: height)
        window = NSWindow(
            contentRect: windowRect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Synapse — Personal Intelligence"
        window.appearance = NSAppearance(named: .darkAqua)
        window.backgroundColor = NSColor(srgbRed: 9.0/255.0, green: 9.0/255.0, blue: 11.0/255.0, alpha: 1.0)
        window.minSize = NSSize(width: 375, height: 600)

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")

        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.uiDelegate = self
        webView.navigationDelegate = self
        webView.setValue(false, forKey: "drawsBackground")

        window.contentView?.addSubview(webView)
        setupMainMenu()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            if let url = URL(string: "http://127.0.0.1:8080") {
                self.webView.load(URLRequest(url: url))
            }
        }
    }

    func startOllamaDaemonIfNeeded() {
        let ollamaPath = "/opt/homebrew/bin/ollama"
        guard FileManager.default.fileExists(atPath: ollamaPath) else { return }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: ollamaPath)
        proc.arguments = ["serve"]
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        self.ollamaServerProcess = proc
    }

    func startFastApiBackendIfNeeded() {
        let projectRoot = "/Users/akash/Documents/projects/Synapse"
        let venvPython = "\(projectRoot)/.venv/bin/python"
        guard FileManager.default.fileExists(atPath: venvPython) else { return }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: venvPython)
        proc.currentDirectoryURL = URL(fileURLWithPath: projectRoot)
        proc.arguments = [
            "-m", "uvicorn", "app.api.server:app",
            "--host", "0.0.0.0", "--port", "8000"
        ]
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = projectRoot
        proc.environment = env
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        self.backendServerProcess = proc
    }

    func startEmbeddedWebServer() {
        guard let resourcePath = Bundle.main.resourcePath else { return }
        let webRoot = (resourcePath as NSString).appendingPathComponent("web")

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        proc.arguments = ["-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", webRoot]
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        try? proc.run()
        self.uiServerProcess = proc
    }

    func applicationWillTerminate(_ notification: Notification) {
        uiServerProcess?.terminate()
        backendServerProcess?.terminate()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func webView(
        _ webView: WKWebView,
        runOpenPanelWith parameters: WKOpenPanelParameters,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping ([URL]?) -> Void
    ) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.beginSheetModal(for: window) { result in
            if result == .OK {
                completionHandler(panel.urls)
            } else {
                completionHandler(nil)
            }
        }
    }

    func setupMainMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        appMenuItem.submenu = appMenu
        appMenu.addItem(withTitle: "Reload UI", action: #selector(reloadPage), keyEquivalent: "r")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit Synapse", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Edit")
        editMenuItem.submenu = editMenu
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")

        NSApp.mainMenu = mainMenu
    }

    @objc func reloadPage() {
        webView.reload()
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
