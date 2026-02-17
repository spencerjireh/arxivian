import { useSettingsStore, DEFAULT_SETTINGS } from '../../../src/stores/settingsStore'

describe('settingsStore', () => {
  beforeEach(() => {
    useSettingsStore.setState({ ...DEFAULT_SETTINGS })
  })

  describe('initial state', () => {
    it('matches DEFAULT_SETTINGS', () => {
      const state = useSettingsStore.getState()
      expect(state.provider).toBe(DEFAULT_SETTINGS.provider)
      expect(state.model).toBe(DEFAULT_SETTINGS.model)
      expect(state.temperature).toBe(DEFAULT_SETTINGS.temperature)
      expect(state.top_k).toBe(DEFAULT_SETTINGS.top_k)
      expect(state.guardrail_threshold).toBe(DEFAULT_SETTINGS.guardrail_threshold)
      expect(state.max_retrieval_attempts).toBe(DEFAULT_SETTINGS.max_retrieval_attempts)
      expect(state.conversation_window).toBe(DEFAULT_SETTINGS.conversation_window)
      expect(state.showInternalSteps).toBe(DEFAULT_SETTINGS.showInternalSteps)
    })
  })

  describe('setters', () => {
    it('setProvider updates provider', () => {
      useSettingsStore.getState().setProvider('openai')
      expect(useSettingsStore.getState().provider).toBe('openai')
    })

    it('setModel updates model', () => {
      useSettingsStore.getState().setModel('gpt-4o')
      expect(useSettingsStore.getState().model).toBe('gpt-4o')
    })

    it('setTemperature updates temperature', () => {
      useSettingsStore.getState().setTemperature(0.8)
      expect(useSettingsStore.getState().temperature).toBe(0.8)
    })

    it('setTopK updates top_k', () => {
      useSettingsStore.getState().setTopK(5)
      expect(useSettingsStore.getState().top_k).toBe(5)
    })

    it('setGuardrailThreshold updates guardrail_threshold', () => {
      useSettingsStore.getState().setGuardrailThreshold(90)
      expect(useSettingsStore.getState().guardrail_threshold).toBe(90)
    })

    it('setMaxRetrievalAttempts updates max_retrieval_attempts', () => {
      useSettingsStore.getState().setMaxRetrievalAttempts(5)
      expect(useSettingsStore.getState().max_retrieval_attempts).toBe(5)
    })

    it('setConversationWindow updates conversation_window', () => {
      useSettingsStore.getState().setConversationWindow(10)
      expect(useSettingsStore.getState().conversation_window).toBe(10)
    })

    it('setShowInternalSteps updates showInternalSteps', () => {
      useSettingsStore.getState().setShowInternalSteps(true)
      expect(useSettingsStore.getState().showInternalSteps).toBe(true)
    })
  })

  describe('resetToDefaults', () => {
    it('restores all settings to defaults', () => {
      useSettingsStore.getState().setProvider('openai')
      useSettingsStore.getState().setTemperature(0.9)
      useSettingsStore.getState().setTopK(10)
      useSettingsStore.getState().setShowInternalSteps(true)

      useSettingsStore.getState().resetToDefaults()

      const state = useSettingsStore.getState()
      expect(state.provider).toBe(DEFAULT_SETTINGS.provider)
      expect(state.temperature).toBe(DEFAULT_SETTINGS.temperature)
      expect(state.top_k).toBe(DEFAULT_SETTINGS.top_k)
      expect(state.showInternalSteps).toBe(false)
    })
  })
})
