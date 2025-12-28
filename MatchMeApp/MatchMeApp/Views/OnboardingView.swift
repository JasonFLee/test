import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var appState: AppState
    @State private var name: String = ""
    @State private var age: String = ""
    @State private var currentPage: Int = 0

    var body: some View {
        ZStack {
            // Background gradient
            LinearGradient(
                gradient: Gradient(colors: [Color.purple.opacity(0.6), Color.pink.opacity(0.6)]),
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 30) {
                Spacer()

                if currentPage == 0 {
                    welcomePage
                } else {
                    profileSetupPage
                }

                Spacer()
            }
            .padding()
        }
    }

    private var welcomePage: some View {
        VStack(spacing: 24) {
            Image(systemName: "heart.circle.fill")
                .font(.system(size: 100))
                .foregroundColor(.white)

            Text("MatchMe")
                .font(.largeTitle)
                .fontWeight(.bold)
                .foregroundColor(.white)

            Text("Find your perfect match\nthrough meaningful conversations")
                .font(.title3)
                .multilineTextAlignment(.center)
                .foregroundColor(.white.opacity(0.9))

            VStack(spacing: 16) {
                FeatureRow(icon: "bubble.left.and.bubble.right.fill", text: "Answer thoughtful questions")
                FeatureRow(icon: "sparkles", text: "AI-powered matching")
                FeatureRow(icon: "heart.fill", text: "Meet compatible people")
            }
            .padding(.top, 20)

            Button(action: {
                withAnimation {
                    currentPage = 1
                }
            }) {
                Text("Get Started")
                    .font(.headline)
                    .foregroundColor(.purple)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.white)
                    .cornerRadius(16)
            }
            .padding(.top, 30)
        }
    }

    private var profileSetupPage: some View {
        VStack(spacing: 24) {
            Text("Let's set up your profile")
                .font(.title)
                .fontWeight(.bold)
                .foregroundColor(.white)

            VStack(spacing: 16) {
                TextField("Your name", text: $name)
                    .textFieldStyle(CustomTextFieldStyle())

                TextField("Your age", text: $age)
                    .textFieldStyle(CustomTextFieldStyle())
                    .keyboardType(.numberPad)
            }
            .padding(.top, 20)

            Button(action: {
                if let ageInt = Int(age), !name.isEmpty {
                    appState.createUser(name: name, age: ageInt)
                }
            }) {
                Text("Continue to Interview")
                    .font(.headline)
                    .foregroundColor(.purple)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(isFormValid ? Color.white : Color.white.opacity(0.5))
                    .cornerRadius(16)
            }
            .disabled(!isFormValid)
            .padding(.top, 30)

            Button(action: {
                withAnimation {
                    currentPage = 0
                }
            }) {
                Text("Back")
                    .foregroundColor(.white)
            }
        }
    }

    private var isFormValid: Bool {
        !name.isEmpty && Int(age) != nil && (Int(age) ?? 0) >= 18
    }
}

struct FeatureRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.white)
                .frame(width: 40)

            Text(text)
                .font(.body)
                .foregroundColor(.white)

            Spacer()
        }
        .padding(.horizontal)
    }
}

struct CustomTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding()
            .background(Color.white)
            .cornerRadius(12)
    }
}

#Preview {
    OnboardingView()
        .environmentObject(AppState())
}
