#pragma once

#include "esphome/core/component.h"
#include "remote_base_ac.h"

namespace esphome {
namespace remote_base {

struct LGACData {
  uint32_t data;
  uint8_t nbits;

  bool operator==(const LGACData &rhs) const { return data == rhs.data && nbits == rhs.nbits; }
};

class LGACProtocol : public RemoteProtocol<LGACData> {
 public:
  void encode(RemoteTransmitData *dst, const LGACData &data) override;
  optional<LGACData> decode(RemoteReceiveData src) override;
  void dump(const LGACData &data) override;
};

DECLARE_REMOTE_PROTOCOL(LGAC)

template<typename... Ts> class LGACAction : public RemoteTransmitterActionBase<Ts...> {
 public:
  TEMPLATABLE_VALUE(uint32_t, data)
  TEMPLATABLE_VALUE(uint8_t, nbits)

  void encode(RemoteTransmitData *dst, Ts... x) override {
    LGACData data{};
    data.data = this->data_.value(x...);
    data.nbits = this->nbits_.value(x...);
    LGACProtocol().encode(dst, data);
  }
};

}  // namespace remote_base
}  // namespace esphome
