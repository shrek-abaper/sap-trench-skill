/**
 * SAP 外向交货单创建工具
 * 使用 SAP JCo 3.0 调用 BAPI_OUTB_DELIVERY_CREATE_STO 创建 STO 类型的外向交货单
 *
 * 编译:
 * javac -cp "sapjco3.jar" SapDeliveryCreator.java
 *
 * 运行 (Linux):
 * java -cp ".:sapjco3.jar" -Djava.library.path=lib/linux SapDeliveryCreator <采购订单号>
 *
 * 运行 (macOS):
 * java -cp ".:sapjco3.jar" -Djava.library.path=lib/macos SapDeliveryCreator <采购订单号>
 *
 * 运行 (Windows):
 * java -cp ".;sapjco3.jar" -Djava.library.path=lib/windows SapDeliveryCreator <采购订单号>
 */

import com.sap.conn.jco.*;
import com.sap.conn.jco.ext.DataProviderException;
import com.sap.conn.jco.ext.DestinationDataEventListener;
import com.sap.conn.jco.ext.DestinationDataProvider;
import com.sap.conn.jco.ext.Environment;

import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

public class SapDeliveryCreator {

    private static final String DESTINATION_NAME = "SAP_DEST";

    /**
     * 自定义目标数据提供者，从环境变量读取配置
     */
    static class InMemoryDestinationDataProvider implements DestinationDataProvider {

        private DestinationDataEventListener eL;
        private HashMap<String, Properties> secureDBStorage = new HashMap<>();

        @Override
        public Properties getDestinationProperties(String destinationName) {
            try {
                Properties p = secureDBStorage.get(destinationName);
                if (p != null && p.isEmpty()) {
                    throw new DataProviderException(DataProviderException.Reason.INVALID_CONFIGURATION,
                            "destination configuration is incorrect", null);
                }
                return p;
            } catch (RuntimeException re) {
                throw new DataProviderException(DataProviderException.Reason.INTERNAL_ERROR, re);
            }
        }

        @Override
        public void setDestinationDataEventListener(DestinationDataEventListener eventListener) {
            this.eL = eventListener;
        }

        @Override
        public boolean supportsEvents() {
            return true;
        }

        void changeProperties(String destName, Properties properties) {
            synchronized (secureDBStorage) {
                if (properties == null) {
                    if (secureDBStorage.remove(destName) != null) {
                        eL.deleted(destName);
                    }
                } else {
                    secureDBStorage.put(destName, properties);
                    eL.updated(destName);
                }
            }
        }
    }

    /**
     * 从环境变量读取SAP连接配置
     */
    private static Properties getPropertiesFromEnv() throws Exception {
        Properties props = new Properties();

        String ahost = getEnvVar("SAP_ASHOST");
        String sysnr = getEnvVar("SAP_SYSNR");
        String client = getEnvVar("SAP_CLIENT");
        String user = getEnvVar("SAP_USER");
        String passwd = getEnvVar("SAP_PASSWORD");

        props.setProperty(DestinationDataProvider.JCO_ASHOST, ahost);
        props.setProperty(DestinationDataProvider.JCO_SYSNR, sysnr);
        props.setProperty(DestinationDataProvider.JCO_CLIENT, client);
        props.setProperty(DestinationDataProvider.JCO_USER, user);
        props.setProperty(DestinationDataProvider.JCO_PASSWD, passwd);

        // 可选参数
        String lang = System.getenv("SAP_LANG");
        if (lang != null && !lang.isEmpty()) {
            props.setProperty(DestinationDataProvider.JCO_LANG, lang);
        } else {
            props.setProperty(DestinationDataProvider.JCO_LANG, "EN");
        }

        // SAP路由器 (可选)
        String router = System.getenv("SAP_SAPROUTER");
        if (router != null && !router.isEmpty()) {
            props.setProperty(DestinationDataProvider.JCO_SAPROUTER, router);
        }

        // 连接池配置
        props.setProperty(DestinationDataProvider.JCO_POOL_CAPACITY, "5");
        props.setProperty(DestinationDataProvider.JCO_PEAK_LIMIT, "10");

        return props;
    }

    /**
     * 获取环境变量，不存在时抛出异常
     */
    private static String getEnvVar(String name) throws Exception {
        String value = System.getenv(name);
        if (value == null || value.trim().isEmpty()) {
            throw new Exception("缺少必要的环境变量: " + name);
        }
        return value;
    }

    /**
     * 注册并配置SAP目标
     */
    private static JCoDestination configureDestination() throws Exception {
        InMemoryDestinationDataProvider provider = new InMemoryDestinationDataProvider();

        if (!Environment.isDestinationDataProviderRegistered()) {
            Environment.registerDestinationDataProvider(provider);
        }

        provider.changeProperties(DESTINATION_NAME, getPropertiesFromEnv());

        return JCoDestinationManager.getDestination(DESTINATION_NAME);
    }

    /**
     * 创建外向交货单（从STO采购订单）
     *
     * @param poNumber STO采购订单号
     * @return 交货单号，失败返回null
     */
    public static DeliveryResult createOutboundDeliveryFromSTO(String poNumber) {
        DeliveryResult result = new DeliveryResult();
        result.success = false;

        try {
            JCoDestination destination = configureDestination();

            // 先获取采购订单的详细信息
            POInfo poInfo = getPOInfo(destination, poNumber);

            if (!poInfo.valid) {
                result.messages.add("无法获取采购订单信息: " + poInfo.errorMessage);
                return result;
            }

            // 调用 BAPI_OUTB_DELIVERY_CREATE_STO 创建交货单
            String deliveryNumber = callDeliveryCreateSTO(destination, poNumber, poInfo);

            if (deliveryNumber != null && !deliveryNumber.isEmpty()) {
                result.success = true;
                result.deliveryNumber = deliveryNumber;
                result.messages.add("外向交货单创建成功");
                result.poInfo = poInfo;
            }
        } catch (JCoException jcoEx) {
            handleJCoException(jcoEx, result);
        } catch (Exception ex) {
            result.messages.add("程序执行异常: " + ex.getClass().getName() + " - " + (ex.getMessage() != null ? ex.getMessage() : "No message"));
            ex.printStackTrace();
        }

        return result;
    }

    /**
     * 获取采购订单信息
     */
    private static POInfo getPOInfo(JCoDestination destination, String poNumber) {
        POInfo poInfo = new POInfo();
        poInfo.valid = false;

        try {
            JCoFunction function = destination.getRepository().getFunction("BAPI_PO_GETDETAIL");
            function.getImportParameterList().setValue("PURCHASEORDER", poNumber);
            function.execute(destination);

            // 获取第一个行项目的信息
            JCoTable items = function.getTableParameterList().getTable("PO_ITEMS");
            if (items.getNumRows() > 0) {
                items.setRow(0);
                poInfo.supplyPlant = items.getString("PLANT");
                poInfo.material = items.getString("MATERIAL");
                poInfo.itemsCount = items.getNumRows();
            }

            // 检查返回消息
            JCoTable returnTable = function.getTableParameterList().getTable("RETURN");
            if (returnTable.getNumRows() > 0) {
                returnTable.setRow(0);
                String type = returnTable.getString("TYPE");
                if ("E".equals(type) || "A".equals(type)) {
                    poInfo.errorMessage = returnTable.getString("MESSAGE");
                    return poInfo;
                }
            }

            poInfo.valid = true;

        } catch (JCoException e) {
            poInfo.errorMessage = "获取采购订单信息失败: " + e.getMessage();
        }

        return poInfo;
    }

    /**
     * 调用 BAPI_OUTB_DELIVERY_CREATE_STO 创建交货单
     */
    private static String callDeliveryCreateSTO(
            JCoDestination destination,
            String poNumber,
            POInfo poInfo
    ) throws JCoException {

        JCoFunction function = null;
        String deliveryNumber = null;

        try {
            // 开始一个 SAP LUW（事务上下文）
            com.sap.conn.jco.JCoContext.begin(destination);
            System.out.println("SAP LUW 已开始");

            // 调用交货单创建BAPI
            function = destination.getRepository().getFunction("BAPI_OUTB_DELIVERY_CREATE_STO");

            // 设置 STOCK_TRANS_ITEMS 表 - 指定要创建交货单的采购订单行项目
            JCoTable stockTransItems = function.getTableParameterList().getTable("STOCK_TRANS_ITEMS");
            stockTransItems.deleteAllRows();

            // 获取采购订单的所有行项目
            JCoFunction getDetails = destination.getRepository().getFunction("BAPI_PO_GETDETAIL");
            getDetails.getImportParameterList().setValue("PURCHASEORDER", poNumber);
            getDetails.execute(destination);

            JCoTable items = getDetails.getTableParameterList().getTable("PO_ITEMS");

            for (int i = 0; i < items.getNumRows(); i++) {
                items.setRow(i);
                String poItem = items.getString("PO_ITEM");
                String poQty = items.getString("QUANTITY");
                String poUnit = items.getString("UNIT");

                stockTransItems.appendRow();
                stockTransItems.setValue("REF_DOC", poNumber);       // 采购订单号
                stockTransItems.setValue("REF_ITEM", poItem);        // 采购订单行号
                stockTransItems.setValue("DLV_QTY", poQty);         // 交货数量
                stockTransItems.setValue("SALES_UNIT", poUnit);     // 销售单位
            }

            // 执行创建交货单BAPI
            System.out.println("正在调用 BAPI_OUTB_DELIVERY_CREATE_STO...");
            function.execute(destination);
            System.out.println("BAPI_OUTB_DELIVERY_CREATE_STO 执行完成");

            // 获取返回的交货单号
            deliveryNumber = function.getExportParameterList().getString("DELIVERY");
            System.out.println("交货单号: " + deliveryNumber);

            // 检查返回消息 - 验证是否成功
            JCoTable returnTable = function.getTableParameterList().getTable("RETURN");
            boolean hasError = false;
            boolean hasSuccessMessage = false;
            StringBuilder errorMsg = new StringBuilder();
            StringBuilder successMsg = new StringBuilder();

            for (int i = 0; i < returnTable.getNumRows(); i++) {
                returnTable.setRow(i);
                String type = returnTable.getString("TYPE");
                String message = returnTable.getString("MESSAGE");
                String id = returnTable.getString("ID");
                String number = returnTable.getString("NUMBER");

                if ("E".equals(type) || "A".equals(type)) {
                    hasError = true;
                    errorMsg.append("[").append(id).append(number).append("] ").append(message).append("; ");
                } else if ("S".equals(type)) {
                    hasSuccessMessage = true;
                    successMsg.append(message).append("; ");
                } else if ("W".equals(type)) {
                    System.out.println("警告: " + message);
                }
            }

            if (hasSuccessMessage) {
                System.out.println("创建交货单成功消息: " + successMsg.toString());
            }

            // 如果没有成功消息但有错误消息，或者生成DN失败，则回滚
            if (hasError || deliveryNumber == null || deliveryNumber.isEmpty()) {
                rollbackTransaction(destination);
                com.sap.conn.jco.JCoContext.end(destination);
                String err = hasError ? errorMsg.toString() :
                              (deliveryNumber == null ? "未生成交货单号" : "交货单号为空");
                throw new JCoException(JCoException.JCO_ERROR_COMMUNICATION, err);
            }

            // 调用 BAPI_TRANSACTION_COMMIT 提交事务
            System.out.println("正在调用 BAPI_TRANSACTION_COMMIT...");
            JCoFunction commitFunction = destination.getRepository().getFunction("BAPI_TRANSACTION_COMMIT");
            commitFunction.getImportParameterList().setValue("WAIT", "X");  // 等待事务完成
            commitFunction.execute(destination);
            System.out.println("BAPI_TRANSACTION_COMMIT 执行完成");

            // 读取 COMMIT 的返回确认是否成功
            boolean commitSuccess = true;
            String commitMessage = "";

            JCoParameterList commitTables = commitFunction.getTableParameterList();
            if (commitTables != null && commitTables.getFieldCount() > 0) {
                try {
                    JCoTable commitReturn = commitTables.getTable("RETURN");
                    for (int i = 0; i < commitReturn.getNumRows(); i++) {
                        commitReturn.setRow(i);
                        String type = commitReturn.getString("TYPE");
                        String message = commitReturn.getString("MESSAGE");
                        if ("E".equals(type) || "A".equals(type)) {
                            commitSuccess = false;
                            commitMessage = message;
                            System.err.println("COMMIT 失败: " + commitMessage);
                            break;
                        } else if ("S".equals(type)) {
                            System.out.println("COMMIT 成功消息: " + message);
                        }
                    }
                } catch (Exception e) {
                    System.out.println("无法读取 COMMIT 返回表: " + e.getMessage());
                }
            }

            if (!commitSuccess) {
                rollbackTransaction(destination);
                com.sap.conn.jco.JCoContext.end(destination);
                throw new JCoException(JCoException.JCO_ERROR_COMMUNICATION, "事务提交失败: " + commitMessage);
            }

            // 结束 SAP LUW
            com.sap.conn.jco.JCoContext.end(destination);
            System.out.println("SAP LUW 已结束");

            System.out.println("事务提交成功，交货单 " + deliveryNumber + " 已保存到 SAP");
            return deliveryNumber;

        } catch (JCoException e) {
            // 发生异常时确保结束 LUW 并回滚事务
            try {
                rollbackTransaction(destination);
                com.sap.conn.jco.JCoContext.end(destination);
            } catch (Exception rollbackEx) {
                // 忽略回滚异常
            }
            throw e;
        }
    }

    /**
     * 提交事务
     */
    private static void commitTransaction(JCoDestination destination) throws JCoException {
        JCoFunction commitFunction = destination.getRepository().getFunction("BAPI_TRANSACTION_COMMIT");
        commitFunction.getImportParameterList().setValue("WAIT", "X");
        commitFunction.execute(destination);
    }

    /**
     * 提交事务并返回返回表
     */
    private static JCoTable commitTransactionWithReturn(JCoDestination destination) throws JCoException {
        JCoFunction commitFunction = destination.getRepository().getFunction("BAPI_TRANSACTION_COMMIT");
        commitFunction.getImportParameterList().setValue("WAIT", "X");
        commitFunction.execute(destination);

        // 检查是否有 RETURN 表参数
        JCoParameterList tableParams = commitFunction.getTableParameterList();
        if (tableParams == null || tableParams.getFieldCount() == 0) {
            // 如果没有 RETURN 表，假设提交成功
            return null;
        }

        try {
            return tableParams.getTable("RETURN");
        } catch (RuntimeException e) {
            // RETURN 表不存在，假设提交成功
            return null;
        }
    }

    /**
     * 事务柜滚
     */
    private static void rollbackTransaction(JCoDestination destination) {
        try {
            JCoFunction rollbackFunction = destination.getRepository().getFunction("BAPI_TRANSACTION_ROLLBACK");
            rollbackFunction.execute(destination);
        } catch (Exception e) {
            // 忽略回滚错误
        }
    }

    /**
     * 判断事务是否成功
     */
    private static boolean isTransactionSuccess(JCoTable returnTable) {
        // 如果没有返回表，假设事务成功（常见于某些 BAPI 不返回 RETURN 表的情况）
        if (returnTable == null) {
            return true;
        }
        if (returnTable.getNumRows() == 0) {
            return true;  // 空返回表表示无错误
        }
        for (int i = 0; i < returnTable.getNumRows(); i++) {
            returnTable.setRow(i);
            String type = returnTable.getString("TYPE");
            if ("E".equals(type) || "A".equals(type)) {
                return false;
            }
        }
        return true;
    }

    /**
     * 处理 JCo 异常
     */
    private static void handleJCoException(JCoException ex, DeliveryResult result) {
        String message = ex.getMessage();
        String key = ex.getKey();

        // 根据异常类型分类处理
        if (message.contains("logon") || message.contains("authentication") || message.contains("user")) {
            result.messages.add("登录失败: 用户名或密码错误");
        } else if (message.contains("authorization") || message.contains("permission")) {
            result.messages.add("权限不足: 用户没有调用 BAPI 的权限");
        } else if (message.contains("communication") || message.contains("connect")) {
            result.messages.add("通信错误: 无法连接到 SAP 系统");
        } else {
            result.messages.add("SAP 业务错误: " + message);
        }
    }

    /**
     * 主函数
     */
    public static void main(String[] args) {
        if (args.length < 1) {
            printUsage();
            System.exit(1);
        }

        String poNumber = args[0];

        try {
            System.out.println("=== SAP 外向交货单创建工具 ===");
            System.out.println("采购订单号: " + poNumber);
            System.out.println();

            DeliveryResult result = createOutboundDeliveryFromSTO(poNumber);

            if (result.success) {
                System.out.println("交货单创建成功!");
                System.out.println();
                System.out.println("采购订单号: " + result.poInfo.supplyPlant);
                System.out.println("交货单号: " + result.deliveryNumber);
                System.out.println("物料数: " + result.poInfo.itemsCount);
                System.out.println();
                System.out.println(result.deliveryNumber);  // 输出用于脚本解析
            } else {
                System.err.println("交货单创建失败:");
                for (String msg : result.messages) {
                    System.err.println("  - " + msg);
                }
                System.exit(1);
            }

        } catch (Exception e) {
            System.err.println("程序执行失败: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    /**
     * 打印用法信息
     */
    private static void printUsage() {
        System.err.println("用法: java SapDeliveryCreator <采购订单号>");
        System.err.println();
        System.err.println("环境变量配置:");
        System.err.println("  SAP_ASHOST     - SAP应用服务器地址 (必填)");
        System.err.println("  SAP_SYSNR      - SAP系统编号，如: 00 (必填)");
        System.err.println("  SAP_CLIENT     - SAP客户端，如: 800 (必填)");
        System.err.println("  SAP_USER       - SAP用户名 (必填)");
        System.err.println("  SAP_PASSWORD   - SAP密码 (必填)");
        System.err.println("  SAP_LANG       - 登录语言 (可选，默认: EN)");
        System.err.println("  SAP_SAPROUTER  - SAP路由器字符串 (可选)");
        System.err.println();
        System.err.println("示例:");
        System.err.println("  export SAP_ASHOST=10.0.0.1");
        System.err.println("  export SAP_SYSNR=00");
        System.err.println("  export SAP_CLIENT=800");
        System.err.println("  export SAP_USER=YOUR_USER");
        System.err.println("  export SAP_PASSWORD=YOUR_PASSWORD");
        System.err.println("  java -cp \".:sapjco3.jar\" -Djava.library.path=lib/linux  SapDeliveryCreator 0123456789  # Linux");
        System.err.println("  java -cp \".:sapjco3.jar\" -Djava.library.path=lib/macos  SapDeliveryCreator 0123456789  # macOS");
        System.err.println("  java -cp \".;sapjco3.jar\" -Djava.library.path=lib/windows SapDeliveryCreator 0123456789  # Windows");
        System.err.println();
        System.err.println("注意事项:");
        System.err.println("  1. 确保 sapjco3.jar 在 classpath 中");
        System.err.println("  2. 确保对应平台的 JCo 本地库在 java.library.path 中");
        System.err.println("     Linux:   libsapjco3.so   (放置于 lib/linux/)");
        System.err.println("     macOS:   libsapjco3.jnilib 或 libsapjco3.dylib (放置于 lib/macos/)");
        System.err.println("     Windows: sapjco3.dll     (放置于 lib/windows/)");
        System.err.println("  3. 使用的 JDK 版本需要与 SAP JCo 兼容");
    }

    /**
     * 采购订单信息类
     */
    static class POInfo {
        boolean valid = false;
        String supplyPlant;
        String material;
        int itemsCount = 0;
        String errorMessage;
    }

    /**
     * 交货单创建结果类
     */
    static class DeliveryResult {
        boolean success;
        String deliveryNumber;
        POInfo poInfo;
        java.util.List<String> messages = new java.util.ArrayList<>();
    }
}