import SwiftUI

struct InterviewView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedOption: Int? = nil
    @State private var isAnimating: Bool = false

    var body: some View {
        ZStack {
            // Background
            Color(UIColor.systemBackground)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                headerView

                // Progress bar
                progressBar
                    .padding(.horizontal)
                    .padding(.top, 20)

                // Question content
                if let question = appState.currentQuestion {
                    questionContent(question: question)
                }

                Spacer()

                // Continue button
                continueButton
                    .padding(.horizontal)
                    .padding(.bottom, 30)
            }
        }
    }

    private var headerView: some View {
        VStack(spacing: 8) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Question \(appState.currentQuestionIndex + 1) of \(appState.questions.count)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    if let question = appState.currentQuestion {
                        Text(question.category.rawValue)
                            .font(.caption)
                            .foregroundColor(.purple)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 4)
                            .background(Color.purple.opacity(0.1))
                            .cornerRadius(12)
                    }
                }

                Spacer()

                Image(systemName: "heart.fill")
                    .foregroundColor(.pink)
                    .font(.title2)
            }
            .padding()
        }
        .background(Color(UIColor.systemBackground))
    }

    private var progressBar: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 6)
                    .cornerRadius(3)

                Rectangle()
                    .fill(
                        LinearGradient(
                            gradient: Gradient(colors: [.purple, .pink]),
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: geometry.size.width * appState.interviewProgress, height: 6)
                    .cornerRadius(3)
                    .animation(.easeInOut(duration: 0.3), value: appState.interviewProgress)
            }
        }
        .frame(height: 6)
    }

    private func questionContent(question: InterviewQuestion) -> some View {
        ScrollView {
            VStack(spacing: 24) {
                // Question text
                Text(question.text)
                    .font(.title2)
                    .fontWeight(.semibold)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                    .padding(.top, 30)

                // Options
                if let options = question.options {
                    VStack(spacing: 12) {
                        ForEach(Array(options.enumerated()), id: \.offset) { index, option in
                            OptionButton(
                                text: option,
                                isSelected: selectedOption == index,
                                action: {
                                    withAnimation(.easeInOut(duration: 0.2)) {
                                        selectedOption = index
                                    }
                                }
                            )
                        }
                    }
                    .padding(.horizontal)
                }
            }
        }
    }

    private var continueButton: some View {
        Button(action: {
            if let selected = selectedOption {
                withAnimation {
                    appState.answerQuestion(selectedOptionIndex: selected)
                    selectedOption = nil
                }
            }
        }) {
            HStack {
                Text(appState.currentQuestionIndex == appState.questions.count - 1 ? "Finish Interview" : "Continue")
                    .font(.headline)

                Image(systemName: "arrow.right")
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding()
            .background(
                selectedOption != nil ?
                LinearGradient(
                    gradient: Gradient(colors: [.purple, .pink]),
                    startPoint: .leading,
                    endPoint: .trailing
                ) :
                LinearGradient(
                    gradient: Gradient(colors: [.gray, .gray]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .cornerRadius(16)
        }
        .disabled(selectedOption == nil)
    }
}

struct OptionButton: View {
    let text: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(text)
                    .font(.body)
                    .multilineTextAlignment(.leading)
                    .foregroundColor(isSelected ? .white : .primary)

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.white)
                }
            }
            .padding()
            .background(
                isSelected ?
                LinearGradient(
                    gradient: Gradient(colors: [.purple, .pink]),
                    startPoint: .leading,
                    endPoint: .trailing
                ) :
                LinearGradient(
                    gradient: Gradient(colors: [Color(UIColor.secondarySystemBackground), Color(UIColor.secondarySystemBackground)]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
            )
            .cornerRadius(12)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.clear : Color.gray.opacity(0.3), lineWidth: 1)
            )
        }
    }
}

#Preview {
    InterviewView()
        .environmentObject(AppState())
}
