import { useEffect, useMemo, useState } from 'react';
import MainScreen from './components/MainScreen';
import ScreenFrame from './components/ScreenFrame';
import ServiceSelect from './components/ServiceSelect';
import IdentityVerify from './components/IdentityVerify';
import ConfirmFee from './components/ConfirmFee';
import { CopyCountPage, IssueContentPage } from './components/IssueContent';
import './styles/App.css';
import { DEFAULT_HISTORY_OPTIONS, LOCAL_SERVICE_CATEGORIES, USER_TYPES } from './data/options';
import {
  connectStomp,
  subscribeFrontAck,
  subscribeUiCommands,
  sendFrontEvent,
  sendUiAck,
  createApplication,
  endSession,
  getServices,
  saveInteractionLog,
  startSession,
  applyAccessibilityAction,
  disconnectStomp,
} from './api/api';

const STEP_MAIN = 'main';
const STEP_SERVICE = 'service';
const STEP_VERIFY = 'verify';
const STEP_ISSUE_CONTENT = 'issue_content';
const STEP_COPY_COUNT = 'copy_count';
const STEP_CONFIRM = 'confirm';

const FEE_PER_COPY = 400;

const initialForm = {
  categoryId: null,
  categoryTitle: '',
  selectedMenuId: null,
  selectedMenuName: '',
  selectedServiceId: '',
  selectedServiceLabel: '',
  residentFront: '',
  residentBack: '',
  issueType: '',
  selectedHistoryOptions: [],
  copyCount: '',
};

export default function App() {
  const [screen, setScreen] = useState(STEP_MAIN);
  const [categories, setCategories] = useState(LOCAL_SERVICE_CATEGORIES);
  const [sessionId, setSessionId] = useState('');
  const [accessibility, setAccessibility] = useState(USER_TYPES.NORMAL);
  const [statusMessage, setStatusMessage] = useState('');
  const [submittedApplicationNo, setSubmittedApplicationNo] = useState('');
  const [form, setForm] = useState(initialForm);

  useEffect(() => {
    let mounted = true;
    let currentSessionId = '';

    async function bootstrap() {
      try {
        await connectStomp();

        await subscribeFrontAck({
          onAck: (payload) => {
            console.log('front ack:', payload);
          },
        });

        const [sessionResult, services] = await Promise.all([startSession('NORMAL'), getServices()]);
        if (!mounted) return;

        const nextSessionId = sessionResult.sessionId || '';
        currentSessionId = nextSessionId;

        setSessionId(nextSessionId);
        setCategories(Array.isArray(services) ? services : LOCAL_SERVICE_CATEGORIES);

        if (sessionResult.accessibility) {
          setAccessibility((prev) => ({
            ...prev,
            ...sessionResult.accessibility,
            fontSize: Number.parseInt(sessionResult.accessibility.fontSize, 10) || prev.fontSize,
          }));
        }

        await subscribeUiCommands({
          sessionId: nextSessionId,
          onCommand: async (message) => {
            if (!message) return;

            const action = message.action;
            const data = message.data || {};

            if (action === 'ADAPT_UI') {
              if (data.accessibility) {
                setAccessibility((prev) => ({
                  ...prev,
                  ...data.accessibility,
                  fontSize: Number.parseInt(data.accessibility.fontSize, 10) || prev.fontSize,
                }));
              }
              await sendUiAck('ADAPT_UI', { sessionId: nextSessionId });
              return;
            }

            if (action === 'MOVE_PAGE') {
              const targetPage = data.page;
              const allowedPages = [
                STEP_MAIN,
                STEP_SERVICE,
                STEP_VERIFY,
                STEP_ISSUE_CONTENT,
                STEP_COPY_COUNT,
                STEP_CONFIRM,
              ];

              if (allowedPages.includes(targetPage)) {
                setScreen(targetPage);
              }
              await sendUiAck('MOVE_PAGE', { sessionId: nextSessionId, page: targetPage });
              return;
            }

            if (action === 'GO_HOME') {
              setForm(initialForm);
              setSubmittedApplicationNo('');
              setStatusMessage('');
              setScreen(STEP_MAIN);
              await sendUiAck('GO_HOME', { sessionId: nextSessionId });
              return;
            }

            if (action === 'SESSION_EXPIRED') {
              setForm(initialForm);
              setSubmittedApplicationNo('');
              setStatusMessage('세션이 만료되었습니다. 처음 화면으로 이동합니다.');
              setScreen(STEP_MAIN);
              return;
            }

            if (action === 'IDLE_WARNING') {
              setStatusMessage(data.message || '잠시 후 처음 화면으로 돌아갑니다.');
            }
          },
        });
      } catch (error) {
        console.error(error);
      }
    }

    bootstrap();

    return () => {
      mounted = false;
      if (currentSessionId) {
        endSession(currentSessionId);
      }
      disconnectStomp();
    };
  }, []);

  const confirmSummary = useMemo(() => {
    const serviceName = form.selectedServiceLabel || form.selectedMenuName || '주민등록등본 발급';
    const issueTypeLabel = form.issueType === 'all' ? '전체발급' : '선택발급';
    return {
      serviceName,
      issueTypeLabel,
      selectedOptions: form.issueType === 'select' ? form.selectedHistoryOptions : [],
      copyCount: form.copyCount || '1',
    };
  }, [form]);

  const totalFee = (Number(form.copyCount) || 0) * FEE_PER_COPY;

  const logAction = async (action, payload = {}) => {
    await saveInteractionLog(sessionId, action, payload);
  };

  const resetToHome = async () => {
    await sendFrontEvent('USER_CANCEL', { sessionId });
    await logAction('GO_HOME');
    setForm(initialForm);
    setSubmittedApplicationNo('');
    setStatusMessage('');
    setScreen(STEP_MAIN);
  };

  const handleAccessibilityAction = async (actionKey) => {
    if (actionKey === 'voiceGuide') {
      setStatusMessage('음성안내는 추후 TTS 모듈과 연결하면 됩니다.');
      await sendFrontEvent('USER_TOUCH', { sessionId, actionKey });
      await logAction('VOICE_GUIDE_CLICK');
      return;
    }

    const nextAccessibility = await applyAccessibilityAction(sessionId, accessibility, actionKey);
    setAccessibility(nextAccessibility);
    await logAction('UPDATE_ACCESSIBILITY', nextAccessibility);
  };

  const handleMainServiceClick = async (item) => {
    await sendFrontEvent('USER_TOUCH', { sessionId, serviceId: item.id });
    await logAction('SELECT_MAIN_MENU', item);

    if (item.type === 'resident') {
      setForm((prev) => ({
        ...prev,
        categoryId: 'certificate',
        categoryTitle: '증명서발급',
        selectedMenuId: item.id,
        selectedMenuName: item.name,
      }));
      setScreen(STEP_SERVICE);
      return;
    }

    setStatusMessage('현재 예시는 주민등록등본/초본 흐름만 구현되어 있습니다.');
  };

  const handleSelectService = async (service) => {
    setForm((prev) => ({
      ...prev,
      selectedServiceId: service.id,
      selectedServiceLabel: service.label,
    }));
    await sendFrontEvent('USER_TOUCH', { sessionId, serviceId: service.id });
    await logAction('SELECT_SERVICE_TYPE', service);
  };

  const handleResidentKeypad = async (key) => {
    setForm((prev) => {
      const frontFull = prev.residentFront.length >= 6;
      if (key === 'X') {
        if (prev.residentBack.length > 0) {
          return { ...prev, residentBack: prev.residentBack.slice(0, -1) };
        }
        return { ...prev, residentFront: prev.residentFront.slice(0, -1) };
      }

      if (!/^\d$/.test(key)) return prev;
      if (!frontFull) return { ...prev, residentFront: `${prev.residentFront}${key}`.slice(0, 6) };
      return { ...prev, residentBack: `${prev.residentBack}${key}`.slice(0, 7) };
    });

    await sendFrontEvent('USER_TOUCH', { sessionId, key, inputType: 'resident_number' });
    await logAction('INPUT_RESIDENT_NUMBER', { key });
  };

  const handleCopyCountKeypad = async (key) => {
    setForm((prev) => {
      if (key === 'X') {
        return { ...prev, copyCount: prev.copyCount.slice(0, -1) };
      }
      if (!/^\d$/.test(key)) return prev;
      const next = `${prev.copyCount}${key}`.replace(/^0+(?=\d)/, '').slice(0, 2);
      return { ...prev, copyCount: next };
    });

    await sendFrontEvent('USER_TOUCH', { sessionId, key, inputType: 'copy_count' });
    await logAction('INPUT_COPY_COUNT', { key });
  };

  const handlePrev = async () => {
    const prevMap = {
      [STEP_SERVICE]: STEP_MAIN,
      [STEP_VERIFY]: STEP_SERVICE,
      [STEP_ISSUE_CONTENT]: STEP_VERIFY,
      [STEP_COPY_COUNT]: STEP_ISSUE_CONTENT,
      [STEP_CONFIRM]: STEP_COPY_COUNT,
    };

    const prev = prevMap[screen];
    if (prev) {
      await sendFrontEvent('USER_CANCEL', { sessionId, from: screen, to: prev });
      await logAction('GO_PREVIOUS', { from: screen, to: prev });
      setScreen(prev);
    }
  };

  const handleNext = async () => {
    const nextMap = {
      [STEP_SERVICE]: STEP_VERIFY,
      [STEP_VERIFY]: STEP_ISSUE_CONTENT,
      [STEP_ISSUE_CONTENT]: STEP_COPY_COUNT,
      [STEP_COPY_COUNT]: STEP_CONFIRM,
    };

    const next = nextMap[screen];
    if (next) {
      await sendFrontEvent('USER_TOUCH', { sessionId, from: screen, to: next, action: 'NEXT' });
      await logAction('GO_NEXT', { from: screen, to: next });
      setScreen(next);
    }
  };

  const handleIssueTypeChange = async (issueType) => {
    setForm((prev) => ({
      ...prev,
      issueType,
      selectedHistoryOptions: issueType === 'all' ? [] : prev.selectedHistoryOptions,
    }));

    await sendFrontEvent('USER_TOUCH', { sessionId, issueType });
  };

  const toggleHistoryOption = async (option) => {
    setForm((prev) => ({
      ...prev,
      selectedHistoryOptions: prev.selectedHistoryOptions.includes(option)
        ? prev.selectedHistoryOptions.filter((item) => item !== option)
        : [...prev.selectedHistoryOptions, option],
    }));

    await sendFrontEvent('USER_TOUCH', { sessionId, option });
  };

  const handleSubmit = async () => {
    const payload = {
      sessionId,
      serviceId: form.selectedServiceId,
      serviceName: confirmSummary.serviceName,
      residentRegistrationNumber: `${form.residentFront}-${form.residentBack}`,
      issueType: form.issueType,
      selectedOptions: form.selectedHistoryOptions,
      copyCount: Number(form.copyCount),
      feePerCopy: FEE_PER_COPY,
      totalFee,
    };

    const result = await createApplication(payload);
    setSubmittedApplicationNo(result.applicationNo || '발급 접수 완료');
    setStatusMessage(`접수가 완료되었습니다. 신청번호: ${result.applicationNo || '임시번호 생성'}`);

    await sendFrontEvent('SERVICE_COMPLETE', {
      sessionId,
      applicationNo: result.applicationNo,
    });
    await logAction('SUBMIT_APPLICATION', result);

    setTimeout(() => {
      resetToHome();
    }, 2500);
  };

  const renderScreen = () => {
    switch (screen) {
      case STEP_MAIN:
        return (
          <MainScreen
            categories={categories}
            onSelectService={handleMainServiceClick}
            onAccessibilityAction={handleAccessibilityAction}
          />
        );
      case STEP_SERVICE:
        return (
          <ServiceSelect
            selectedServiceId={form.selectedServiceId}
            onSelect={handleSelectService}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_VERIFY:
        return (
          <IdentityVerify
            residentFront={form.residentFront}
            residentBack={form.residentBack}
            onKeypadPress={handleResidentKeypad}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_ISSUE_CONTENT:
        return (
          <IssueContentPage
            issueType={form.issueType}
            options={DEFAULT_HISTORY_OPTIONS}
            selectedOptions={form.selectedHistoryOptions}
            onIssueTypeChange={handleIssueTypeChange}
            onToggleOption={toggleHistoryOption}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_COPY_COUNT:
        return (
          <CopyCountPage
            copyCount={form.copyCount}
            onKeypadPress={handleCopyCountKeypad}
            onHome={resetToHome}
            onPrev={handlePrev}
            onNext={handleNext}
          />
        );
      case STEP_CONFIRM:
        return (
          <ConfirmFee
            summary={confirmSummary}
            fee={FEE_PER_COPY}
            totalFee={totalFee}
            onHome={resetToHome}
            onPrev={handlePrev}
            onSubmit={handleSubmit}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="app-shell">
      <ScreenFrame accessibility={accessibility}>
        {renderScreen()}
        {statusMessage ? <div className="status-message">{statusMessage}</div> : null}
        {submittedApplicationNo ? <div className="status-message">신청번호: {submittedApplicationNo}</div> : null}
      </ScreenFrame>
    </div>
  );
}