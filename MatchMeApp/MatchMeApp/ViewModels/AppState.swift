import Foundation
import SwiftUI

class AppState: ObservableObject {
    @Published var currentUser: User?
    @Published var isOnboarded: Bool = false
    @Published var hasCompletedInterview: Bool = false
    @Published var matches: [Match] = []
    @Published var currentQuestionIndex: Int = 0
    @Published var interviewResponses: [InterviewResponse] = []

    let questions: [InterviewQuestion] = InterviewQuestion.defaultQuestions
    private let matchingService = MatchingService()

    // Mock users for demo purposes
    private var mockUsers: [User] = []

    init() {
        setupMockUsers()
    }

    var currentQuestion: InterviewQuestion? {
        guard currentQuestionIndex < questions.count else { return nil }
        return questions[currentQuestionIndex]
    }

    var interviewProgress: Double {
        Double(currentQuestionIndex) / Double(questions.count)
    }

    var isInterviewComplete: Bool {
        currentQuestionIndex >= questions.count
    }

    // MARK: - Onboarding

    func createUser(name: String, age: Int) {
        currentUser = User(name: name, age: age)
        isOnboarded = true
    }

    // MARK: - Interview

    func answerQuestion(selectedOptionIndex: Int) {
        guard let question = currentQuestion else { return }

        let response = InterviewResponse(
            questionId: question.id,
            answer: question.options?[selectedOptionIndex] ?? "",
            selectedOptionIndex: selectedOptionIndex
        )

        interviewResponses.append(response)
        currentQuestionIndex += 1

        if isInterviewComplete {
            completeInterview()
        }
    }

    func completeInterview() {
        guard var user = currentUser else { return }
        user.interviewResponses = interviewResponses
        user.isInterviewComplete = true
        currentUser = user
        hasCompletedInterview = true
        generateMatches()
    }

    // MARK: - Matching

    func generateMatches() {
        guard let user = currentUser else { return }
        matches = matchingService.generateMatches(for: user, from: mockUsers)
    }

    // MARK: - Mock Data

    private func setupMockUsers() {
        // Create mock users with pre-filled interview responses
        let mockProfiles: [(name: String, age: Int, responses: [Int])] = [
            ("Alex", 28, [0, 1, 1, 2, 1, 3, 0, 1, 0, 1]),
            ("Jordan", 26, [1, 2, 2, 1, 2, 1, 2, 0, 0, 2]),
            ("Taylor", 30, [2, 0, 0, 0, 0, 0, 1, 2, 1, 0]),
            ("Casey", 27, [0, 1, 1, 2, 1, 2, 0, 1, 0, 1]),
            ("Morgan", 29, [3, 3, 3, 3, 3, 2, 3, 3, 2, 3]),
            ("Riley", 25, [1, 2, 1, 1, 2, 1, 2, 1, 0, 2]),
            ("Avery", 31, [0, 0, 0, 1, 1, 3, 0, 0, 0, 1]),
            ("Quinn", 24, [2, 1, 2, 2, 0, 1, 1, 2, 1, 2])
        ]

        for (index, profile) in mockProfiles.enumerated() {
            var responses: [InterviewResponse] = []

            for (qIndex, question) in questions.enumerated() {
                let selectedIndex = profile.responses[qIndex]
                let response = InterviewResponse(
                    questionId: question.id,
                    answer: question.options?[selectedIndex] ?? "",
                    selectedOptionIndex: selectedIndex
                )
                responses.append(response)
            }

            let user = User(
                name: profile.name,
                age: profile.age,
                bio: "Hey there! I'm \(profile.name), looking to meet someone special.",
                profileImageName: "person.circle.fill",
                interviewResponses: responses,
                isInterviewComplete: true
            )

            mockUsers.append(user)
        }
    }

    // MARK: - Reset

    func reset() {
        currentUser = nil
        isOnboarded = false
        hasCompletedInterview = false
        matches = []
        currentQuestionIndex = 0
        interviewResponses = []
    }
}
