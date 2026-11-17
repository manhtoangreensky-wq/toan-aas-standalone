import {pageMetaRenderer} from "./chat-page-meta-runtime.mjs";
import {resizeCopyContext} from "./image-resize-plain-copy-runtime.mjs";
const render=await pageMetaRenderer();
process.stdout.write(JSON.stringify(Object.fromEntries(["vi","en","zh"].map(locale=>
  [locale,render(locale,"/image/resize",resizeCopyContext()).html]))));
