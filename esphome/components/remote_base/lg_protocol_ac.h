#pragma once

#include "esphome/core/component.h"
#include "remote_base.h"

namespace esphome {
namespace remote_base {

struct LGacData {
  uint32_t data;
  uint8_t nbits;

  bool operator==(const LGacData &rhs) const { return data == rhs.data && nbits == rhs.nbits; }
};

class LGacProtocol : public RemoteProtocol<LGacData> {
 public:
  void encode(RemoteTransmitData *dst, const LGacData &data) override;
  optional<LGacData> decode(RemoteReceiveData src) override;
  void dump(const LGacData &data) override;
};

DECLARE_REMOTE_PROTOCOL(LGAC)

template<typename... Ts> class LGacAction : public RemoteTransmitterActionBase<Ts...> {
 public:
  TEMPLATABLE_VALUE(uint32_t, data)
  TEMPLATABLE_VALUE(uint8_t, nbits)

  void encode(RemoteTransmitData *dst, Ts... x) override {
    LGacData data{};
    data.data = this->data_.value(x...);
    data.nbits = this->nbits_.value(x...);
    LGacProtocol().encode(dst, data);
  }
};

}  // namespace remote_base
}  // namespace esphome
