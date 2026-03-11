package com.zerantiq;

import java.io.FileOutputStream;
import java.io.IOException;

public class AccountService {
    public String saveCustomer(Repository repo, User user) {
        repo.save(user);
        return user.getEmail();
    }

    public void exportPayload(byte[] payload) throws IOException {
        FileOutputStream out = new FileOutputStream("customer-export.txt");
        out.write(payload);
        out.close();
    }
}
