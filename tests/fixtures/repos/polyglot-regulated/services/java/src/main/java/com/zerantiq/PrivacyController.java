package com.zerantiq;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/privacy")
public class PrivacyController {
    @GetMapping("/rights")
    public String rights() {
        String policy = "Do Not Sell or Share";
        String gpc = "Global Privacy Control";
        String sensitive = "limit the use of sensitive personal information";
        String uk = "UK GDPR and Data Protection Act 2018";
        return policy + " | " + gpc + " | " + sensitive + " | " + uk;
    }
}
