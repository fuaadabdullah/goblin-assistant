import Document, { Html, Head, Main, NextScript } from 'next/document';
import { fontVariables } from '../theme/fonts';

export default class MyDocument extends Document {
  render() {
    return (
      <Html lang="en" className={fontVariables}>
        <Head>
          <meta name="theme-color" content="#071117" />
          <link rel="icon" href="/favicon.svg" />
          <link rel="apple-touch-icon" href="/GoblinOSIcon.png" />
          <link rel="manifest" href="/site.webmanifest" />
        </Head>
        <body>
          <Main />
          <NextScript />
        </body>
      </Html>
    );
  }
}
