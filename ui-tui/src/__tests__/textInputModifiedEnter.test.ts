import { describe, expect, it } from 'vitest'

import { isModifiedEnterNewlineIntent, shouldPreserveRawLfNewlineIntent } from '../components/textInput.js'

describe('modified Enter newline intent', () => {
  it('treats explicit modified Return keys as newline intent', () => {
    expect(
      isModifiedEnterNewlineIntent({
        eventRaw: '\r',
        key: { return: true, shift: true },
        env: {},
        platform: 'linux',
      }),
    ).toBe(true)

    expect(
      isModifiedEnterNewlineIntent({
        eventRaw: '\r',
        key: { return: true, ctrl: true },
        env: {},
        platform: 'linux',
      }),
    ).toBe(true)
  })

  it('keeps plain CR Return as submit intent', () => {
    expect(
      isModifiedEnterNewlineIntent({
        eventRaw: '\r',
        key: { return: true },
        env: { TERM_PROGRAM: 'WezTerm' },
        platform: 'linux',
      }),
    ).toBe(false)
  })

  it('preserves raw LF as newline intent in terminals where plain Enter is distinct CR', () => {
    expect(
      isModifiedEnterNewlineIntent({
        eventRaw: '\n',
        key: { return: true },
        env: { TERM_PROGRAM: 'WezTerm' },
        platform: 'linux',
      }),
    ).toBe(true)

    expect(
      isModifiedEnterNewlineIntent({
        eventRaw: '\n',
        key: { return: true },
        env: { TERM_PROGRAM: 'WarpTerminal' },
        platform: 'darwin',
      }),
    ).toBe(true)
  })

  it('does not treat bare LF as newline intent in local thin PTY fallbacks', () => {
    expect(
      isModifiedEnterNewlineIntent({
        eventRaw: '\n',
        key: { return: true },
        env: { TERM: 'xterm-256color' },
        platform: 'linux',
      }),
    ).toBe(false)
  })

  it('preserves raw LF over SSH, WSL, and Windows Terminal where Ctrl+Enter arrives as c-j', () => {
    expect(shouldPreserveRawLfNewlineIntent({ SSH_CONNECTION: 'host 1 host 2' }, 'linux')).toBe(true)
    expect(shouldPreserveRawLfNewlineIntent({ WT_SESSION: 'session' }, 'linux')).toBe(true)
    expect(shouldPreserveRawLfNewlineIntent({ WSL_DISTRO_NAME: 'Ubuntu' }, 'linux')).toBe(true)
    expect(shouldPreserveRawLfNewlineIntent({}, 'win32')).toBe(true)
  })
})
