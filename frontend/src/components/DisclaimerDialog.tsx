import React from "react";
import { Info } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface DisclaimerDialogProps {
  isDark?: boolean;
}

const DisclaimerDialog: React.FC<DisclaimerDialogProps> = ({
  isDark = false,
}) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="flex items-center gap-1.5 font-medium text-muted-foreground/70 hover:text-muted-foreground transition-colors underline underline-offset-2 decoration-dotted">
          <Info className="w-3 h-3" />
          免責聲明
        </button>
      </DialogTrigger>
      <DialogContent
        className={`sm:max-w-[600px] max-h-[80vh] overflow-y-auto ${
          isDark ? "bg-black" : "bg-white"
        }`}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Info className="w-5 h-5 text-blue-500" />
            免責聲明
          </DialogTitle>
          <strong>最後更新日期：2025 年 7 月 13 日</strong>

          <p>
            歡迎您使用「立委
            AI」網站（以下稱「本網站」）。為保障使用者權益並明確說明本網站之法律責任與權利義務，特此聲明如下。若您使用本網站，即視為已閱讀、了解並同意受本免責聲明之所有約束；若您不同意，請即停止使用本網站。
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              一、服務性質與資料來源
            </h4>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>
                本網站透過{" "}
                <a
                  href="https://openfun.tw/"
                  className="text-blue-300 hover:text-blue-400 underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  歐噴有限公司
                </a>{" "}
                提供之{" "}
                <a
                  href="https://dataly.openfun.app/"
                  className="text-blue-300 hover:text-blue-400 underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  立院統合資料網 API
                </a>{" "}
                擷取立法院、各地方議會及其他公部門公開之影音與文字資料，再以人工智慧模型進行事實整理、索引與搜尋輔助。
              </li>
              <li>
                所有原始影音、逐字稿、會議紀錄、法案文本等，均屬其原發布單位所有；本網站僅提供重新組織與檢索之介面，不對內容進行刪改。
              </li>
              <li>
                本網站所顯示之外部連結（例如立法院議事轉播影片、政府開放資料平台網址），僅為使用者進一步查證、比對之便利；其內容與可用性由各該網站自行負責，本網站不保證其完整性或持續可用性。
              </li>
            </ol>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              二、準確性與時效性
            </h4>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>
                本網站致力於提供準確、最新的資訊，惟因資料可能隨時間更新、轉載或被原單位更正，且
                AI 整理過程仍具推論誤差，
                <strong>
                  本網站不對任何資訊之正確性、完整性、適時性做出明示或默示之保證
                </strong>
                。
              </li>
              <li>
                使用者如需引用或依據本網站訊息進行決策（包括但不限於法律行動、公共評論、商業分析或媒體報導等），應以官方原始資料為最終依據，並自行負完全責任。本網站不對任何因使用、誤用或依賴本網站資訊而導致之直接或間接損失負責。
              </li>
            </ol>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              三、非專業建議
            </h4>
            <p>
              本網站所有內容僅供一般資訊參考之用，
              <strong>不構成法律、政治、投資、醫療或其他專業意見</strong>
              。如有專業需求，請諮詢具有相應資格之專業人士。
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              四、智慧財產權
            </h4>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>
                本網站所呈現之文字、排版、介面設計、AI
                生成之摘要或標籤等，除屬公共領域或依法得合理使用之部分外，其著作權由本網站或合法權利人享有。
              </li>
              <li>
                使用者得依《中華民國著作權法》「合理使用」原則閱讀、分享並引用本網站內容；超出合理使用範圍者，須先取得本網站及／或權利人書面授權。
              </li>
            </ol>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              五、使用者行為
            </h4>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>
                使用者不得以任何方式逆向工程、惡意爬蟲、過度請求或其他影響本網站正常運作之行為。
              </li>
              <li>
                使用者如對資料完整性或權利歸屬有疑慮，或發現不實、侵權內容，可透過客服信箱{" "}
                <a
                  href="mailto:ly@codeer.ai"
                  className="text-blue-300 hover:text-blue-400 underline"
                >
                  ly@codeer.ai
                </a>{" "}
                提出；本網站將依法或依自有判斷於合理期間內處理。
              </li>
              <li>
                使用者應確保其輸入之提問及指令不含違法或侵權內容；若因使用者提問導致
                AI
                產生之回覆違反憲法、法律、其他規範或公序良俗，相關法律責任概由使用者自行承擔，本網站不負任何責任。
              </li>
            </ol>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              六、服務中斷、修改與終止
            </h4>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>
                本網站有權於任何時間暫停、修改或終止全部或部分服務或內容，且無需事先通知使用者。
              </li>
              <li>
                本網站對因系統維護、第三方設備故障、不可抗力或其他非可歸責於本網站之事由，導致服務中斷或資料損失，不負任何賠償責任。
              </li>
            </ol>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">
              七、適用法律與管轄法院
            </h4>
            <p>
              本免責聲明之解釋與適用，以及因使用本網站所生之爭議，均依《中華民國（臺灣）法律》處理；如涉訴訟，以臺灣臺北地方法院為第一審管轄法院。
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-2">八、修訂</h4>
            <p>
              本網站得隨時修訂本免責聲明並於本頁公告最新版本，不另行個別通知。建議您定期查閱，持續使用即表示同意更新後之內容。
            </p>
          </div>

          <div className="pt-4 border-t">
            <p>
              若您對本免責聲明或本網站有任何疑問，歡迎來信{" "}
              <a
                href="mailto:ly@codeer.ai"
                className="text-blue-300 hover:text-blue-400 underline"
              >
                ly@codeer.ai
              </a>{" "}
              與我們聯繫。
            </p>
          </div>
        </DialogHeader>
      </DialogContent>
    </Dialog>
  );
};

export default DisclaimerDialog;
