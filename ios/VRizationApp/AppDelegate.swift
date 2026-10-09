import UIKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        if ProcessInfo.processInfo.arguments.contains("--reset-preferences"), let id = Bundle.main.bundleIdentifier {
            UserDefaults.standard.removePersistentDomain(forName: id)
        }
        return true
    }

    func application(_ application: UIApplication, configurationForConnecting session: UISceneSession,
                     options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: "VRization", sessionRole: session.role)
        if session.role == .windowApplication { configuration.delegateClass = SceneDelegate.self }
        return configuration
    }

    func application(_ application: UIApplication,
                     supportedInterfaceOrientationsFor window: UIWindow?) -> UIInterfaceOrientationMask { .landscape }
}

/// Bind the window to its actual scene geometry instead of portrait UIScreen bounds.
/// There is one viewer scene; secondary displays do not create another USB listener.
final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private var viewer: ViewerController? { window?.rootViewController as? ViewerController }

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        guard session.role == .windowApplication, let scene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: scene)
        window.rootViewController = ViewerController()
        self.window = window
        window.makeKeyAndVisible()
    }
    func sceneWillResignActive(_ scene: UIScene) { viewer?.suspendSession() }
    func sceneDidBecomeActive(_ scene: UIScene) { viewer?.resumeDisplay() }
    func sceneDidDisconnect(_ scene: UIScene) {
        viewer?.suspendSession()
        window = nil
    }
}
