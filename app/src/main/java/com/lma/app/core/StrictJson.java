package com.lma.app.core;
import org.json.*;
import java.util.*;

/** RFC 8259 shape check before the platform's deliberately permissive JSONObject parser. */
public final class StrictJson {
    private final String text;private int at;
    private StrictJson(String value){text=value;}
    public static JSONObject object(String value)throws Exception{if(value.length()>32000)throw new IllegalArgumentException("JSON 参数过长");StrictJson p=new StrictJson(value);p.space();if(p.at==value.length()||value.charAt(p.at)!='{')throw new IllegalArgumentException("工具参数必须为 JSON 对象");p.value(0);p.space();if(p.at!=value.length())throw new IllegalArgumentException("JSON 尾部有多余内容");return new JSONObject(value);}
    private void space(){while(at<text.length()&&" \r\n\t".indexOf(text.charAt(at))>=0)at++;}
    private void expect(char c){space();if(at>=text.length()||text.charAt(at++)!=c)throw new IllegalArgumentException("无效的 JSON 参数");}
    private String string()throws Exception{space();int start=at;expect('"');while(at<text.length()){char c=text.charAt(at++);if(c=='"')return new JSONTokener(text.substring(start,at)).nextValue().toString();if(c<32)break;if(c=='\\'){if(at>=text.length())break;char escape=text.charAt(at++);if(escape=='u'){for(int i=0;i<4;i++)if(at>=text.length()||Character.digit(text.charAt(at++),16)<0)throw new IllegalArgumentException("JSON Unicode 转义无效");}else if("\"\\/bfnrt".indexOf(escape)<0)throw new IllegalArgumentException("JSON 转义无效");}}throw new IllegalArgumentException("JSON 字符串不完整");}
    private void value(int depth)throws Exception{space();if(depth>16||at>=text.length())throw new IllegalArgumentException("JSON 嵌套或长度无效");char c=text.charAt(at);
        if(c=='{'){at++;space();Set<String> keys=new HashSet<>();if(at<text.length()&&text.charAt(at)=='}'){at++;return;}while(true){String key=string();if(!keys.add(key))throw new IllegalArgumentException("JSON 不允许重复字段");expect(':');value(depth+1);space();if(at<text.length()&&text.charAt(at)=='}'){at++;return;}expect(',');}}
        else if(c=='['){at++;space();if(at<text.length()&&text.charAt(at)==']'){at++;return;}while(true){value(depth+1);space();if(at<text.length()&&text.charAt(at)==']'){at++;return;}expect(',');}}
        else if(c=='"')string();else{int start=at;while(at<text.length()&&",]} \r\n\t".indexOf(text.charAt(at))<0)at++;String token=text.substring(start,at);if(!token.matches("true|false|null|-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?"))throw new IllegalArgumentException("JSON 值无效");}
    }
}
