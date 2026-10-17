import { useState } from 'react';
import Review from './Review.jsx';
import Learn from './Learn.jsx';

export default function App() {
  const [tab, setTab] = useState('review');
  return (
    <>
      <header>
        <b className="logo">V-Chess</b>
        {['review', 'learn'].map((t) => (
          <button key={t} className={tab === t ? 'tab on' : 'tab'} onClick={() => setTab(t)}>
            {t === 'review' ? 'Review' : 'Learn chess'}
          </button>
        ))}
      </header>
      {/* both stay mounted so switching tabs doesn't lose your game */}
      <div hidden={tab !== 'review'}><Review /></div>
      <div hidden={tab !== 'learn'}><Learn /></div>
    </>
  );
}
