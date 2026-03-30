import React, { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';

const logoChars = 'ORATO.AI'.split('');

const Footer = () => {
  const logoRef = useRef(null);
  const isInView = useInView(logoRef, { once: true, amount: 0.4 });
  const [openPopup, setOpenPopUp] = useState(false);

  const variants = {
    visible: (i) => ({
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 100,
        damping: 13,
        duration: 0.45,
        delay: i * 0.045
      }
    }),
    hidden: { y: 48, opacity: 0 }
  };

  const handleNewsLetterData = (e) => {
    e.preventDefault();
    const target = e.target;
    const formData = new FormData(target);
    const clientEmail = formData.get('newsletter_email');

    if (!clientEmail) return;

    setOpenPopUp(true);
    target.reset();

    setTimeout(() => {
      setOpenPopUp(false);
    }, 2200);
  };

  return (
    <footer className="landing-footer-wrap">
      <div className="landing-footer-shell">
        <div className="container landing-footer-inner">
        <div className="landing-footer-top">
          <div>
            <h2 className="landing-footer-title">Build better speaking habits, session by session.</h2>
            <p className="landing-footer-sub">Get occasional updates when we ship improvements to speech, visual, and content analysis.</p>

            <div className="landing-newsletter-row">
              <form onSubmit={handleNewsLetterData} className="landing-newsletter-form">
                <input
                  type="email"
                  name="newsletter_email"
                  className="landing-newsletter-input"
                  placeholder="Your email"
                  required
                />
                <button type="submit" className="landing-newsletter-btn" aria-label="Join newsletter">
                  Join
                </button>
              </form>
              {openPopup && <span className="landing-newsletter-confirm">Thanks, you are on the list.</span>}
            </div>
          </div>

          <div className="landing-footer-links">
            <div>
              <h4>Sitemap</h4>
              <ul>
                <li><Link to="/">Home</Link></li>
                <li><Link to="/signin">Login</Link></li>
                <li><Link to="/signup">Sign Up</Link></li>
                <li><Link to="/upload">Upload</Link></li>
              </ul>
            </div>

            <div>
              <h4>Social</h4>
              <ul>
                <li><a href="https://www.linkedin.com/in/awais-khan-mwt/" target="_blank" rel="noreferrer">LinkedIn</a></li>
                <li><a href="https://www.linkedin.com/in/shayan0773/" target="_blank" rel="noreferrer">Team Updates</a></li>
                <li><a href="https://www.linkedin.com/in/ali-haider-cs/" target="_blank" rel="noreferrer">Research</a></li>
              </ul>
            </div>
          </div>
        </div>

        <div className="landing-footer-logo-strip" ref={logoRef}>
          <motion.div className="landing-footer-logo-row" initial="hidden" animate={isInView ? 'visible' : 'hidden'}>
            {logoChars.map((char, index) => (
              <motion.span key={`${char}-${index}`} custom={index} variants={variants}>
                {char}
              </motion.span>
            ))}
          </motion.div>
        </div>

        <div className="landing-footer-bottom">
          <span>© {new Date().getFullYear()} Orato AI. All rights reserved.</span>
          <a href="#">Privacy Policy</a>
        </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;